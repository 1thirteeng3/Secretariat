use serde::{Serialize, Deserialize};
use std::fs;
use std::path::PathBuf;
use tauri::State;
use chrono::Utc;

#[derive(Serialize, Deserialize, Debug)]
pub struct Note {
    pub id: String,
    pub title: String,
    pub content: String,
    pub created_at: String,
    pub tags: Vec<String>
}

// TODO: Use a proper AppState to store the Vault Path
pub struct VaultState {
    pub vault_path: std::sync::Mutex<PathBuf>,
}

#[tauri::command]
pub fn create_note(
    state: State<'_, VaultState>,
    title: String,
    content: String,
    tags: Vec<String>
) -> Result<String, String> {
    let vault_path = state.vault_path.lock().map_err(|e| e.to_string())?.clone();
    
    // Robust sanitization (RUST-02)
    let filename = sanitize_filename(&title);
    let full_path = vault_path.join(&filename);

    if full_path.exists() {
        return Err("Note already exists".to_string());
    }

    let frontmatter = format!(
        "---\nid: {}\ntitle: {}\ncreated_at: {}\ntags: {:?}\n---\n\n",
        uuid::Uuid::new_v4(),
        title,
        Utc::now().to_rfc3339(),
        tags
    );

    let final_content = format!("{}{}", frontmatter, content);

    fs::write(&full_path, final_content).map_err(|e| e.to_string())?;

    Ok(filename)
}

/// Pure function for RUST-02 Test
pub fn sanitize_filename(title: &str) -> String {
    let re = regex::Regex::new(r"[<>:\|?*]").unwrap();
    let safe_title = title.replace("/", "-").replace("\\", "-");
    let safe_title = re.replace_all(&safe_title, "_");
    format!("{}.md", safe_title)
}

#[tauri::command]
pub fn get_app_theme(state: State<'_, VaultState>) -> Result<String, String> {
    let vault_path = state.vault_path.lock().map_err(|e| e.to_string())?.clone();
    let theme_path = vault_path.join("hack.css");

    if theme_path.exists() {
        fs::read_to_string(theme_path).map_err(|e| e.to_string())
    } else {
        Ok("".to_string())
    }
}

#[tauri::command]
pub fn read_note(state: State<'_, VaultState>, filename: String) -> Result<String, String> {
    let vault_path = state.vault_path.lock().map_err(|e| e.to_string())?.clone();
    let full_path = vault_path.join(filename);

    fs::read_to_string(full_path).map_err(|e| e.to_string())
}
