use serde::{Serialize, Deserialize};
use tauri::command;
use reqwest::Client;
use std::env;
use dotenv::dotenv;

#[derive(Serialize, Deserialize)]
pub struct AIRequest {
    pub input_text: String,
    pub context_notes: Vec<String>, 
}

#[derive(Serialize, Deserialize, Debug)]
pub struct AIParsedResponse {
    pub title: String,
    pub markdown_content: String,
    pub tags: Vec<String>,
    pub suggested_links: Vec<String>
}

// Internal struct for DeepSeek API
#[derive(Serialize)]
struct DeepSeekMessage {
    role: String,
    content: String,
}

#[derive(Serialize)]
struct DeepSeekRequest {
    model: String,
    messages: Vec<DeepSeekMessage>,
    stream: bool,
    response_format: Option<serde_json::Value>,
}

#[derive(Deserialize)]
struct DeepSeekChoice {
    message: DeepSeekMessageContent,
}

#[derive(Deserialize)]
struct DeepSeekMessageContent {
    content: String,
}

#[derive(Deserialize)]
struct DeepSeekResponse {
    choices: Vec<DeepSeekChoice>,
}

#[command]
pub async fn process_input_with_ai(input: String) -> Result<AIParsedResponse, String> {
    dotenv().ok();
    let api_key = env::var("DEEPSEEK_API_KEY").unwrap_or_default();
    
    if api_key.is_empty() {
        return Err("DEEPSEEK_API_KEY not set".to_string());
    }

    let client = Client::new();
    
    // We use R1 (reasoner) for creating structured valid notes from raw input
    let model = "deepseek-reasoner".to_string(); 

    let schema_example = serde_json::json!({
        "title": "Concise Title",
        "markdown_content": "# Title\n\nBody...",
        "tags": ["#tag1", "#tag2"],
        "suggested_links": ["[[Existing Note]]"]
    });

    let system_prompt = format!(
        "You are Secretariat, a Second Brain AI.\nYour goal is to parse raw user input (voice transcript or text) into a STRUCTURED Markdown note.\n\nOutput strictly in JSON format matching this schema:\n{}",
        serde_json::to_string_pretty(&schema_example).unwrap()
    );

    let payload = DeepSeekRequest {
        model,
        messages: vec![
            DeepSeekMessage { role: "system".into(), content: system_prompt.into() },
            DeepSeekMessage { role: "user".into(), content: input },
        ],
        stream: false,
        response_format: Some(serde_json::json!({ "type": "json_object" })),
    };

    let res = client.post("https://api.deepseek.com/chat/completions")
        .header("Authorization", format!("Bearer {}", api_key))
        .header("Content-Type", "application/json")
        .json(&payload)
        .send()
        .await
        .map_err(|e| e.to_string())?;

    if !res.status().is_success() {
        return Err(format!("API Error: {}", res.status()));
    }

    let response_body: DeepSeekResponse = res.json().await.map_err(|e| e.to_string())?;
    
    let content = &response_body.choices[0].message.content;
    
    // Parse the JSON string from the AI
    let parsed: AIParsedResponse = serde_json::from_str(content).map_err(|e| format!("Failed to parse AI JSON: {}", e))?;

    Ok(parsed)
}

#[command]
pub async fn chat_with_vault(query: String, context_notes: Vec<String>) -> Result<String, String> {
    dotenv().ok();
    let api_key = env::var("DEEPSEEK_API_KEY").unwrap_or_default();
    let client = Client::new();
    
    // V3 for Chat
    let model = "deepseek-chat".to_string();

    let system_prompt = format!(
        "You are Secretariat. Answer the user question based STRICTLY on the following context notes:\n\n{:?}", 
        context_notes
    );

    let payload = DeepSeekRequest {
        model,
        messages: vec![
            DeepSeekMessage { role: "system".into(), content: system_prompt },
            DeepSeekMessage { role: "user".into(), content: query },
        ],
        stream: false,
        response_format: None,
    };

    let res = client.post("https://api.deepseek.com/chat/completions")
        .header("Authorization", format!("Bearer {}", api_key))
        .header("Content-Type", "application/json")
        .json(&payload)
        .send()
        .await
        .map_err(|e| e.to_string())?;

    if !res.status().is_success() {
         return Err(format!("API Error: {}", res.status()));
    }

    let response_body: DeepSeekResponse = res.json().await.map_err(|e| e.to_string())?;
    Ok(response_body.choices[0].message.content.clone())
}
