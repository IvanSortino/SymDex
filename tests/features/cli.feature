Feature: CLI Commands

  Background:
    Given a temporary directory with Python source files has been indexed

  Scenario: Index a folder via CLI
    When I run "symdex index" on the temporary directory
    Then the command exits with code 0
    And the output contains indexing statistics

  Scenario: Search for a symbol via CLI
    When I run "symdex search" with query "parse_file"
    Then the command exits with code 0
    And the output contains at least one symbol row

  Scenario: Search returns error for unknown symbol
    When I run "symdex search" with query "nonexistent_xyz_symbol"
    Then the command exits with code 1
    And the output contains "Error"

  Scenario: List repos via CLI
    When I run "symdex repos"
    Then the command exits with code 0
    And the output contains at least one repo name

  Scenario: JSON flag returns valid JSON for search
    When I run "symdex search" with query "parse_file" and flag "--json"
    Then the command exits with code 0
    And the output is valid JSON containing a "symbols" key

  Scenario: Outline a file via CLI
    When I run "symdex outline" on an indexed file
    Then the command exits with code 0
    And the output contains at least one symbol row

  Scenario: Text search via CLI
    When I run "symdex text" with query "def parse_file"
    Then the command exits with code 0
    And the output contains at least one result row

  Scenario: Invalidate cache via CLI
    When I run "symdex invalidate" for the indexed repo
    Then the command exits with code 0
    And the output contains the invalidated count
