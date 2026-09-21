from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
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
        AWAITING_REVIEW = "AWAITING_REVIEW", "Awaiting review"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    source = models.CharField(max_length=10, choices=ImportSource.choices)
    status = models.CharField(max_length=20, choices=ImportStatus.choices, default=ImportStatus.PENDING)
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


class TransactionCategoryRule(BaseModel):
    """A category choice previously taught by the owner."""

    normalized_description = models.CharField(max_length=255)
    kind_of_transaction = models.CharField(
        max_length=10,
        choices=Transaction.KindOfTransaction.choices,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="categorization_rules",
    )
    times_applied = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["normalized_description"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "normalized_description", "kind_of_transaction"],
                name="unique_owner_transaction_category_rule",
            )
        ]

    def __str__(self):
        return f"{self.normalized_description} -> {self.category.name}"


class TransactionImportItem(BaseModel):
    """A parsed transaction kept as a draft until categorization is approved."""

    class ReviewStatus(models.TextChoices):
        PENDING_REVIEW = "PENDING_REVIEW", "Pending review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    class CategorizationSource(models.TextChoices):
        IMPORT = "IMPORT", "Imported value"
        RULE = "RULE", "Learned rule"
        AI = "AI", "AI suggestion"
        MANUAL = "MANUAL", "Manual choice"

    transaction_import = models.ForeignKey(
        TransactionImport,
        on_delete=models.CASCADE,
        related_name="items",
    )
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="import_item",
    )
    kind_of_transaction = models.CharField(
        max_length=10,
        choices=Transaction.KindOfTransaction.choices,
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    date = models.DateTimeField()
    description = models.TextField()
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="import_items",
    )
    suggested_category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suggested_import_items",
    )
    categorization_source = models.CharField(
        max_length=10,
        choices=CategorizationSource.choices,
        default=CategorizationSource.IMPORT,
    )
    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING_REVIEW,
    )
    ai_confidence = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    ai_reasoning = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["transaction_import", "created_at"]

    def __str__(self):
        return f"{self.description[:30]} - {self.review_status}"
