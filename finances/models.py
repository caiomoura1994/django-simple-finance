from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from core.base_model import BaseModel

class Category(BaseModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_categories')
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
        unique_together = ['owner', 'slug']

    def __str__(self):
        return f"{self.pk} - {self.name}"

class Account(BaseModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    balance = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0.00,
        validators=[MinValueValidator(0.00)]
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_accounts')
    class Meta:
        ordering = ['name']
        unique_together = ['owner', 'slug']

    def __str__(self):
        return f"{self.pk} - {self.name} - {self.balance}"

class Transaction(BaseModel):
    class KindOfTransaction(models.TextChoices):
      INCOME = "INCOME", "Income"
      EXPENSE = "EXPENSE", "Expense"

    kind_of_transaction = models.CharField(
        max_length=10, 
        choices=KindOfTransaction.choices,
        default=KindOfTransaction.EXPENSE
    )
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    date = models.DateTimeField(default=timezone.now)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='transactions')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    
    # # Fields for AI processing
    # receipt_image = models.ImageField(upload_to='receipts/%Y/%m/', null=True, blank=True)
    # ai_processed = models.BooleanField(default=False)
    # ai_confidence_score = models.FloatField(null=True, blank=True)
    # original_text = models.TextField(blank=True, help_text="Original text extracted from receipt/image")


    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.pk} - {self.date.strftime('%Y-%m-%d')} - {self.description[:30]}"

class TransactionImport(BaseModel):
    class ImportSource(models.TextChoices):
        EXCEL = "EXCEL", "Excel File"
        OFX = "OFX", "OFX File"
        IMAGE = "IMAGE", "Image with AI"
        API = "API", "API Integration"
        MANUAL = "MANUAL", "Manual Entry"

    class ImportStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    source = models.CharField(max_length=10, choices=ImportSource.choices)
    status = models.CharField(max_length=10, choices=ImportStatus.choices, default=ImportStatus.PENDING)
    file = models.FileField(upload_to='imports/%Y/%m/', null=True, blank=True)
    total_items = models.IntegerField(default=0)
    processed_items = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transaction_imports')
    celery_task_id = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.source} Import - {self.created_at}"