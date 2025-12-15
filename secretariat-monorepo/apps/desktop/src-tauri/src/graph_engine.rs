use serde::Serialize;
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;
use std::sync::Mutex;
use regex::Regex;
use glob::glob;
use tauri::State;
use crate::vault_manager::VaultState;

#[derive(Serialize, Clone)]
pub struct GraphNode {
    pub id: String,
    pub label: String,
    pub weight: usize, // Calculated by number of connections
}

#[derive(Serialize, Clone)]
pub struct GraphLink {
    pub source: String,
    pub target: String,
}

#[derive(Serialize)]
pub struct GraphData {
    pub nodes: Vec<GraphNode>,
    pub links: Vec<GraphLink>,
}

pub struct GraphState {
    // Cache structure could go here
    pub last_data: Mutex<Option<GraphData>>,
}

impl GraphState {
    pub fn new() -> Self {
        Self {
            last_data: Mutex::new(None),
        }
    }
}

#[tauri::command]
pub fn rebuild_graph(
    vault_state: State<'_, VaultState>,
    graph_state: State<'_, GraphState>
) -> Result<GraphData, String> {
    let vault_path = vault_state.vault_path.lock().map_err(|e| e.to_string())?.clone();
    let pattern = vault_path.join("**/*.md");
    let pattern_str = pattern.to_str().ok_or("Invalid vault path")?;

    let mut nodes_map: HashMap<String, usize> = HashMap::new(); // ID -> Weight
    let mut links: HashSet<(String, String)> = HashSet::new();
    
    // 1. First Pass: Collect all Nodes and parse Links
    println!("Scanning Vault at: {}", pattern_str);
    let mut file_count = 0;
    for entry in glob(pattern_str).map_err(|e| e.to_string())? {
        match entry {
            Ok(path) => {
                file_count += 1;
                let file_stem = path.file_stem().unwrap().to_str().unwrap().to_string();
                // Initialize node in map if not exists
                nodes_map.entry(file_stem.clone()).or_insert(0);

                if let Ok(content) = fs::read_to_string(&path) {
                    let extracted = extract_links(&content);
                    for target in extracted {
                        links.insert((file_stem.clone(), target));
                    }
                }
            },
            Err(e) => println!("Error reading file: {:?}", e),
        }
    }
    println!("Found {} files in vault.", file_count);

    // 2. Second Pass: Calculate Weights (Degree Centrality)
    // We only count connections where both nodes exist in our vault for strict graph, 
    // BUT for a "Second Brain", a link to a non-existent note is a "Ghost Node".
    // We will include Ghost Nodes with weight 1.
    
    let mut final_links: Vec<GraphLink> = Vec::new();

    for (source, target) in links {
        // Increment weight for Source
        *nodes_map.entry(source.clone()).or_insert(0) += 1;
        
        // Increment weight for Target (even if it doesn't exist as a file yet)
        *nodes_map.entry(target.clone()).or_insert(0) += 1;

        final_links.push(GraphLink { source, target });
    }

    let final_nodes: Vec<GraphNode> = nodes_map.into_iter().map(|(id, weight)| {
        GraphNode {
            label: id.clone(), // In V0 ID is the Label
            id,
            weight
        }
    }).collect();

    let data = GraphData {
        nodes: final_nodes,
        links: final_links
    };

    // Update Cache
    *graph_state.last_data.lock().map_err(|e| e.to_string())? = Some(GraphData {
        nodes: data.nodes.clone(),
        links: data.links.clone()
    });

    Ok(data)
}

/// Pure function for RUST-03 Test
pub fn extract_links(content: &str) -> Vec<String> {
    let re = Regex::new(r"\[\[(.*?)\]\]").unwrap();
    re.captures_iter(content)
        .filter_map(|cap| cap.get(1).map(|m| m.as_str().to_string()))
        .collect()
}
