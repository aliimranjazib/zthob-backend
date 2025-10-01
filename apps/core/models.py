from django.db import models
from django.contrib.auth import get_user_model

User=get_user_model()

class BaseModel(models.Model):
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    created_by=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="%(class)s_created")
    

    class Meta:
        abstract=True
        ordering=['-created_at']
