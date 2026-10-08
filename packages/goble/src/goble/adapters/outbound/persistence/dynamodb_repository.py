import json

from goble.domain.models import Job


class DynamoDBJobRepository:
    def __init__(self, table_name: str) -> None:
        import boto3  # import diferido: el core no depende de boto3 en tests

        self._table = boto3.resource("dynamodb").Table(table_name)

    def save(self, job: Job) -> None:
        item = job.to_dict()
        # DynamoDB no acepta float: serializamos los campos libres como JSON
        item["payload"] = json.dumps(item["payload"])
        item["result"] = json.dumps(item["result"]) if item["result"] is not None else None
        self._table.put_item(Item={k: v for k, v in item.items() if v is not None})

    def get(self, job_id: str) -> Job | None:
        item = self._table.get_item(Key={"id": job_id}).get("Item")
        if not item:
            return None
        item["payload"] = json.loads(item["payload"])
        item["result"] = json.loads(item["result"]) if item.get("result") else None
        return Job.from_dict(item)
