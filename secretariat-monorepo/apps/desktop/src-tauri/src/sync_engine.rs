use std::env;
use std::path::PathBuf;
use std::fs;
use reqwest::Client;
use serde_json::json;

pub struct SupabaseClient {
    url: String,
    key: String,
    client: Client,
}

impl SupabaseClient {
    pub fn new() -> Self {
        dotenv::dotenv().ok();
        let url = env::var("SUPABASE_URL").expect("SUPABASE_URL not set");
        let key = env::var("SUPABASE_KEY").expect("SUPABASE_KEY not set");
        
        Self {
            url,
            key,
            client: Client::new(),
        }
    }

    pub async fn list_bucket_files(&self, bucket_id: &str) -> Result<Vec<String>, String> {
        let endpoint = format!("{}/storage/v1/object/list/{}", self.url, bucket_id);
        
        let res = self.client.post(&endpoint)
            .header("Authorization", format!("Bearer {}", self.key))
            .header("ApiKey", &self.key)
            .header("Content-Type", "application/json")
            .json(&json!({
                "prefix": "",
                "limit": 100,
                "offset": 0,
                "sortBy": {
                    "column": "name",
                    "order": "asc"
                }
            }))
            .send()
            .await
            .map_err(|e| e.to_string())?;

        if !res.status().is_success() {
             return Err(format!("Supabase Error: {}", res.status()));
        }

        let body: serde_json::Value = res.json().await.map_err(|e| e.to_string())?;
        
        // Parse "name" fields
        let files = body.as_array()
            .ok_or("Invalid response format")?
            .iter()
            .filter_map(|item| item["name"].as_str().map(|s| s.to_string()))
            .collect();

        Ok(files)
    }

    pub async fn upload_file(&self, bucket_id: &str, filename: &str, content: Vec<u8>) -> Result<(), String> {
        let encoded_filename = urlencoding::encode(filename);
        let endpoint = format!("{}/storage/v1/object/{}/{}", self.url, bucket_id, encoded_filename);
        
        let res = self.client.post(&endpoint)
            .header("Authorization", format!("Bearer {}", self.key))
            .header("ApiKey", &self.key) // Supabase storage requires verify
             // For update/upsert usually we use POST with x-upsert header or PUT
            .header("x-upsert", "true") 
            .body(content)
            .send()
            .await
            .map_err(|e| e.to_string())?;

        if !res.status().is_success() {
             let status = res.status();
             let text = res.text().await.unwrap_or_else(|_| "No body".to_string());
             return Err(format!("Upload Error {}: {}", status, text));
        }

        Ok(())
    }

    pub async fn download_file(&self, bucket_id: &str, filename: &str) -> Result<String, String> {
        // Use authenticated endpoint for RLS buckets
        let encoded_filename = urlencoding::encode(filename);
        let endpoint = format!("{}/storage/v1/object/{}/{}", self.url, bucket_id, encoded_filename);

        let res = self.client.get(&endpoint)
            .header("Authorization", format!("Bearer {}", self.key))
            .header("ApiKey", &self.key)
            .send()
            .await
            .map_err(|e| e.to_string())?;

        if !res.status().is_success() {
            return Err(format!("Download Error: {}", res.status()));
        }

        let content = res.text().await.map_err(|e| e.to_string())?;
        Ok(content)
    }
}

use serde::{Serialize, Deserialize};
use std::collections::HashMap;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct SyncState {
    pub last_synced_at: String, // ISO 8601
    pub device_id: String,
}

impl SyncState {
    pub fn new(device_id: String) -> Self {
        Self {
            last_synced_at: "1970-01-01T00:00:00Z".to_string(),
            device_id,
        }
    }
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct NoteSyncMetadata {
    pub id: String,
    pub updated_at: String,
    pub version: u64,
}

#[derive(Debug)]
pub struct SyncPlan {
    pub to_upload: Vec<String>,   // ID
    pub to_download: Vec<String>, // ID
    pub conflicts: Vec<String>,   // ID
}

pub struct SyncEngine;

impl SyncEngine {
    pub async fn run_sync(vault_path: PathBuf) -> Result<String, String> {
        let client = SupabaseClient::new();
        
        let remote_index_res = client.download_file("vault", "index.json").await;
        // Load Remote Index
        let mut remote_index: HashMap<String, NoteSyncMetadata> = match remote_index_res {
            Ok(json_str) => serde_json::from_str(&json_str).unwrap_or_default(),
            Err(_) => HashMap::new() 
        };

        // Load Local Index with Paths
        let (local_index, id_to_path) = Self::scan_local_vault(&vault_path)?;
        
        let plan = Self::calculate_sync_plan(&local_index, &remote_index);
        let mut uploads_count = 0;

        // 4. Execute Uploads
        for id in plan.to_upload {
            if let Some(path) = id_to_path.get(&id) {
                if let Ok(content) = fs::read(path) {
                    let filename = path.file_name().unwrap().to_str().unwrap();
                    // Upload File
                    client.upload_file("vault", filename, content).await?;
                    
                    // Update Remote Index in Memory
                    if let Some(meta) = local_index.get(&id) {
                         remote_index.insert(id.clone(), meta.clone());
                    }
                    uploads_count += 1;
                }
            }
        }
        
        // 5. Save New Index to Remote
        if uploads_count > 0 {
             let index_json = serde_json::to_string(&remote_index).map_err(|e| e.to_string())?;
             client.upload_file("vault", "index.json", index_json.into_bytes()).await?;
        }

        Ok(format!("Sync Complete. Uploaded: {}. Remote Index Size: {}", uploads_count, remote_index.len()))
    }
    
    pub fn scan_local_vault(vault_path: &PathBuf) -> Result<(HashMap<String, NoteSyncMetadata>, HashMap<String, PathBuf>), String> {
        let mut index = HashMap::new();
        let mut paths = HashMap::new();
        let pattern = vault_path.join("**/*.md");
        let pattern_str = pattern.to_str().ok_or("Invalid vault path")?;

        for entry in glob::glob(pattern_str).map_err(|e| e.to_string())? {
            if let Ok(path) = entry {
                if let Ok(content) = fs::read_to_string(&path) {
                    if let Some(metadata) = Self::parse_frontmatter(&content) {
                        index.insert(metadata.id.clone(), metadata.clone());
                        paths.insert(metadata.id.clone(), path);
                    }
                }
            }
        }
        Ok((index, paths))
    }

    fn parse_frontmatter(content: &str) -> Option<NoteSyncMetadata> {
        if content.starts_with("---") {
            if let Some(end) = content[3..].find("---") {
                let yaml_str = &content[3..end+3];
                 #[derive(Deserialize)]
                struct MinimalMeta {
                    id: String,
                    #[serde(default)] 
                    updated_at: String,
                    #[serde(default)] 
                    version: u64,
                }
                
                if let Ok(meta) = serde_yaml::from_str::<MinimalMeta>(yaml_str) {
                    return Some(NoteSyncMetadata {
                        id: meta.id,
                        updated_at: meta.updated_at,
                        version: meta.version
                    });
                }
            }
        }
        None
    }
    
    pub fn calculate_sync_plan(
        local_files: &HashMap<String, NoteSyncMetadata>,
        remote_files: &HashMap<String, NoteSyncMetadata>
    ) -> SyncPlan {
        let mut plan = SyncPlan {
            to_upload: Vec::new(),
            to_download: Vec::new(),
            conflicts: Vec::new(),
        };

        // 1. Check Local files against Remote
        for (id, local_meta) in local_files {
            match remote_files.get(id) {
                Some(remote_meta) => {
                    // Both exist. Compare.
                    if local_meta.version > remote_meta.version {
                         // We are ahead. Upload.
                         plan.to_upload.push(id.clone());
                    } else if remote_meta.version > local_meta.version {
                        // Remote is ahead. Download.
                        plan.to_download.push(id.clone());
                    } else {
                        // Versions equal.
                    }
                },
                None => {
                    // Local exists, Remote doesn't. Upload (New file).
                    plan.to_upload.push(id.clone());
                }
            }
        }

        // 2. Check Remote files that don't exist Locally
        for (id, _remote_meta) in remote_files {
            if !local_files.contains_key(id) {
                plan.to_download.push(id.clone());
            }
        }

        plan
    }
}

#[tauri::command]
pub async fn sync_vault(state: tauri::State<'_, crate::vault_manager::VaultState>) -> Result<String, String> {
    let vault_path = state.vault_path.lock().map_err(|e| e.to_string())?.clone();
    SyncEngine::run_sync(vault_path).await
}
