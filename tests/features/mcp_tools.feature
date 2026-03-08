Feature: MCP Server Tools

  Background:
    Given a temporary directory with Python source files has been indexed

  Scenario: Index a folder and return a summary
    When I call index_folder with the temporary directory path
    Then the response contains "indexed" count greater than 0
    And the response contains a "repo" name
    And the response contains a "db_path"

  Scenario: Search for an existing symbol by name
    When I call search_symbols with query "parse_file"
    Then the response contains a "symbols" list
    And the first symbol has fields "name", "file", "kind", "start_byte", "end_byte"

  Scenario: Search for a symbol that does not exist
    When I call search_symbols with query "nonexistent_xyz_abc_symbol"
    Then the response is an error envelope with code 404
    And the error key is "symbol_not_found"

  Scenario: Get source of a symbol by byte offset
    Given I have a symbol with a known start_byte and end_byte
    When I call get_symbol with those byte offsets
    Then the response contains a non-empty "source" string

  Scenario: Get outline of a file
    When I call get_file_outline with a known indexed file
    Then the response contains a non-empty "symbols" list

  Scenario: Get repository overview
    When I call get_repo_outline for an indexed repo
    Then the response contains "tree" as a string
    And the response contains "stats" with "files" greater than 0

  Scenario: List repositories after indexing
    When I call list_repos
    Then the response contains a "repos" list with at least one entry

  Scenario: Invalidate cache for a specific file
    When I call invalidate_cache for a specific indexed file
    Then the response contains "invalidated" count greater than 0

  Scenario: Missing required parameter returns error
    When I call search_symbols without providing a query
    Then the response is an error envelope with code 400
    And the error key is "invalid_request"
