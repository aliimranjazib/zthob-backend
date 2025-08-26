from rest_framework.response import Response

def api_response(*,success:bool, message:str, data:dict=None, errors:dict=None, status_code:int=200):
    return Response({
        'success':success,
        'message':message,
        'data':data,
        'error':errors
    }, status=status_code )
    
    
    