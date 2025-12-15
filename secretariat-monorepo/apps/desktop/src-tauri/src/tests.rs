#[cfg(test)]
mod verification_tests {
    use crate::vault_manager::sanitize_filename;
    use crate::graph_engine::extract_links;

    // RUST-02: Filename Sanitization
    #[test]
    fn test_rust_02_filename_sanitization() {
        let input = "Nota / De : Teste <Illegal> *";
        let expected = "Nota - De _ Teste _Illegal_ _.md";
        let result = sanitize_filename(input);
        
        assert_eq!(result, expected, "Filename sanitization failed to match RUST-02 requirement");
    }

    #[test]
    fn test_sanitization_basics() {
        assert_eq!(sanitize_filename("Simple"), "Simple.md");
        assert_eq!(sanitize_filename("Date/Time"), "Date-Time.md");
    }

    // RUST-03: Graph Engine Topology
    #[test]
    fn test_rust_03_link_extraction() {
        let content = "
        # Note A
        This is a note linking to [[Note B]] and [[Ghost Node]].
        Also a link to [[Note C]].
        ";
        
        let links = extract_links(content);
        
        assert!(links.contains(&"Note B".to_string()));
        assert!(links.contains(&"Ghost Node".to_string()));
        assert!(links.contains(&"Note C".to_string()));
        assert_eq!(links.len(), 3);
    }
}
