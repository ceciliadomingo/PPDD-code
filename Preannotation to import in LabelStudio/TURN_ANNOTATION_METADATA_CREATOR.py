import datetime
import pytz # Defines timezones

# TFunction to create a metadata file for the TURN annotation tool.
def turn_annotation_metadata_creator(annotation_number, turn_mentions, task_number, project_number, person_ID,json_file_shortened, transcript, turn_ID):

    uk_timezone = pytz.timezone('Europe/London')
    metadata = {"id":annotation_number,
                "annotations": [{
                "id": task_number, 
                "completed_by": person_ID,
                "result": turn_mentions,
                "was_cancelled": False,
                "ground_truth": False,
                "created_at": datetime.datetime.now(uk_timezone).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                "updated_at": datetime.datetime.now(uk_timezone).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                "draft_created_at": datetime.datetime.now(uk_timezone).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                "lead_time": 6.66, 
                "prediction": {},
                "result_count": 0,
                "unique_id": turn_ID,
                "import_id": "null",
                "last_action": "null",
                "task": task_number,
                "project": project_number,
                "updated_by": person_ID,
                "parent_prediction": "null",
                "parent_annotation": "null",
                "last_created_by": "null"}],
        "file_upload": json_file_shortened,
        "drafts": [],
        "predictions": [],
        "data": {
            "text": transcript
        },
        "meta": {"turn_ID":turn_ID},
        "created_at": datetime.datetime.now(uk_timezone).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
        "updated_at": datetime.datetime.now(uk_timezone).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
        "inner_id": annotation_number,
        "total_annotations": 1,
        "cancelled_annotations": 0,
        "total_predictions": 0,
        "comment_count": 0,
        "unresolved_comment_count": 0,
        "last_comment_updated_at": "null",
        "project": project_number,
        "updated_by": person_ID,
        "comment_authors": []
    }
    return metadata