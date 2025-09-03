from typing import Union
from fastapi import APIRouter

router = APIRouter()

@router.get("/stores/{store_id}")
def read_item(store_id: str, q: Union[str, None] = None):
    store = {
        "id":"xxxxxxxx",
        "storeName":"目元専門サロン1",
        "address":"東京都中央区銀座６－１３－９ GIRAC GINZA ６階",
        "content":"格闘家YouTuberの朝倉未来がプロデュースした目元専門の美容エステサロン! \n 【月～土】11:00～20:00/【日・祝】10:00～19:00",
        "lat":35.689501,
        "lng":141.691722,
        "tags":["眼精疲労","シミケア","肌質改善","毛穴洗浄"] 
    }

    return store
