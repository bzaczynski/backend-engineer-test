# Backend Engineer Test

Solution for a job screening test.

## Prerequisites

* Python 3.7
* [Poetry](https://poetry.eustace.io/)

## Installation

```shell
$ cd backend-engineer-test
$ poetry install
```

## Running

### Data Import

```shell
$ poetry run articles-import --csv data/articles.csv --db data/database.db [--chunk 10000]
```

### REST API Server

```shell
$ poetry run articles-serve data/database.db [--port 8080]
```

Available endpoints:

* http://localhost:8080/
* http://localhost:8080/login
* http://localhost:8080/logout
* http://localhost:8080/articles/5W8N-MNB1-F04Y-T38C-00000-00
* http://localhost:8080/articles?keyword=foo
* http://localhost:8080/next-article

## Testing

```shell
$ poetry run pytest -s
```
