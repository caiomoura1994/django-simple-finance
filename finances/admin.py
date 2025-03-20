from django.contrib import admin

from finances.models import Transaction, Category, Account

class CategoryInline(admin.TabularInline):
    model = Category

class AccountInline(admin.TabularInline):
    model = Account

class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'description', 'amount', 'category', 'account', 'kind_of_transaction')
    list_filter = ('category', 'account', 'kind_of_transaction')
    search_fields = ('description',)
    list_per_page = 10
    # inlines = [CategoryInline, AccountInline]

admin.site.register(Transaction, TransactionAdmin)
admin.site.register(Category)
admin.site.register(Account)
