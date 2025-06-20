from collections import defaultdict
from fastapi import BackgroundTasks, HTTPException

from scrap import get_comments
from db_services import add_comments_bulk
from services import predict_judol_comments, predict_spam_comments, predict_sentimen_comments
from preprocess import preprocess_text

async def get_comments_and_process(video_id: str, background_tasks: BackgroundTasks):
    try:
        
        output_data = get_comments(video_id)
        
        comments=[]
        cids=[]
        spamDict = defaultdict(list)

        for row in output_data:
            comments.append(row['text'])
            cids.append(row['cid'])
            spamDict[row['author']].append({"cid":row["cid"], "text":row["text"]})

        processed_texts, feature_list = preprocess_text(comments)

        # add bg task biar dijalanin di bg
        background_tasks.add_task(predict_judol_comments, cids, processed_texts, feature_list)
        background_tasks.add_task(predict_spam_comments, spamDict)
        background_tasks.add_task(predict_sentimen_comments, cids, processed_texts)

        # run dan tunggu ampe kelar
        await add_comments_bulk(output_data)

        # Periksa jika worker mengembalikan pesan error
        if isinstance(output_data, dict) and 'error' in output_data:
            raise HTTPException(status_code=500, detail=f"error: {output_data['error']}")

        return {"success":True}

    except Exception as e:
        # Untuk error lainnya
        raise HTTPException(status_code=500, detail=f"Terjadi kesalahan internal: {str(e)}")
