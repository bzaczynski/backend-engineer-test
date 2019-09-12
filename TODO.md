# TODO

## Import Script

* clarify what to do with the missing article IDs (currently the entire article is skipped)
* clarify how to tokenize (e.g. how to handle special characters, use nltk?)
* consider using native full-text search built-in to some RDBMS instead of manual tokenizing 
* allow to resume the script from the last index
* allow to run the script starting from the given index to run multiple instances in parallel
* modularize the script into smaller functions
* impose constraints on the tables (add primary key to reject duplicates when the script gets executed multiple times)
* add a primary key or index on the tokenized words table
* test the script against corner cases
* replace SQLite with other RDBMS
* add unit tests
* add more logging

## REST API Server

* clarify what should happen when all articles read by a user (currently wraps around already read articles)
* add code to create the necessary tables
* add paging to articles found by keyword
* define data model in terms of SQLAlchemy
* replace low-level SQL queries with higher level ORM abstractions
* ensure the tables are created if not found
* modularize the script into submodules
* replace magic numbers with constants
* parameterize the script (e.g. port number)
* add unit tests
* add more logging

## Misc.

* add Docker
* add GitHub repository
* gitignore.io
