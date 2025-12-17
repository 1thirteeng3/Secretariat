mod vault_manager;
mod ai_orchestrator;
mod graph_engine;
mod sync_engine;
mod tests;

use std::sync::Mutex;
use std::path::PathBuf;
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let path_resolver = app.path();
            let docs_dir = path_resolver.document_dir().unwrap_or(PathBuf::from("."));
            let vault_path = docs_dir.join("SecretariatVault");
            
            if !vault_path.exists() {
                std::fs::create_dir_all(&vault_path)?;
            }
            
            app.manage(vault_manager::VaultState {
                vault_path: Mutex::new(vault_path),
            });
            
            app.manage(graph_engine::GraphState::new());
            
            Ok(())
        })
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            vault_manager::create_note,
            vault_manager::read_note,
            vault_manager::get_app_theme,
            ai_orchestrator::process_input_with_ai,
            ai_orchestrator::chat_with_vault,
            graph_engine::rebuild_graph,
            sync_engine::sync_vault
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
