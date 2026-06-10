from django.contrib import admin

from .models import ShippingMethod, ShippingRule


class ShippingRuleInline(admin.TabularInline):
    model = ShippingRule
    extra = 1


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ("name_ru", "code", "eta_days_min", "eta_days_max", "is_active")
    list_editable = ("is_active",)
    inlines = [ShippingRuleInline]


@admin.register(ShippingRule)
class ShippingRuleAdmin(admin.ModelAdmin):
    list_display = ("method", "region", "cost", "free_above")
    list_filter = ("method",)
    search_fields = ("region",)
