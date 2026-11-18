# Benchmark component: dataset, rule engine, scorer, Collector. Talks to the reader over HTTP.
FROM python:3.12-slim
RUN pip install --no-cache-dir jsonschema==4.26.0
WORKDIR /app
COPY cdb cdb
COPY collector collector
COPY schema schema
COPY data/cases.jsonl data/clauses.jsonl data/
ENV READER_URL=http://reader:8080/v1
ENTRYPOINT ["python", "-m", "cdb.run"]
CMD ["--reader", "llm", "--split", "test", "--out", "/results"]
