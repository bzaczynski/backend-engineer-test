#!/usr/bin/env python

from typing import Generator

import argparse
import logging
import re

import numpy
import pandas
import sqlalchemy

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Entry point to the script."""
    try:
        args = parse_args()
        populate_database(args.db, args.csv, args.chunk_size)
    except KeyboardInterrupt:
        logger.warning('Aborted')
    except Exception as ex:
        logger.error('Unable to import data: %s', ex)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', metavar='<path>', required=True)
    parser.add_argument('--db', metavar='<path>', required=True)
    parser.add_argument('--chunk', type=int, default=10_000, dest='chunk_size')
    return parser.parse_args()


def tokenize(text: str) -> Generator[str, None, None]:
    """Return a generator of lowercase words."""
    return (
        re.sub('[^0-9a-zA-Z]+', '', token.strip().lower())
        for token in re.split(r'\s+', text)
        if token != ''
    )


def populate_database(db_path: str, csv_path: str, chunk_size: int) -> None:
    """Connect to a database and populate it with the data from CSV file."""

    logger.info('Populating "%s" from "%s"', db_path, csv_path)

    database = sqlalchemy.create_engine(f'sqlite:///{db_path}')
    data_frame: pandas.DataFrame
    for data_frame in pandas.read_csv(csv_path, chunksize=chunk_size):
        try:
            data_frame.dropna(axis=0, inplace=True)  # skip missing values
            if len(data_frame) > 0:
                pointers = numpy.append(data_frame['article_id'].values[1:], [''])
                data_frame['next_article_id'] = pointers
                data_frame.to_sql('articles',
                                  database,
                                  if_exists='append',
                                  chunksize=chunk_size)
                logger.info(f'Processed chunk with {len(data_frame)} rows')
        except Exception as ex:
            logger.error('Unable to process chunk of CSV', ex)

        if len(data_frame) > 0:
            logger.info(f'Tokenizing a chunk of articles')

            # tokenize article contents into words
            tokens_series = data_frame['content'].apply(tokenize).values
            for j, article_id in enumerate(data_frame['article_id'].values):
                tokens = list(tokens_series[j])
                tokens_frame = pandas.DataFrame({
                    'article_id': [article_id] * len(tokens),
                    'token': tokens
                })

                # append rows to "tokens" table
                tokens_frame.to_sql('tokens',
                                    database,
                                    if_exists='append',
                                    index=False,
                                    chunksize=chunk_size)


if __name__ == '__main__':
    main()
