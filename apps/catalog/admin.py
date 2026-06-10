from django.contrib import admin

from .models import League, Product, ProductImage, Team


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title_ru", "category", "team", "league", "season", "size", "price", "stock", "is_active")
    list_filter = ("category", "league", "team", "size", "is_active")
    search_fields = ("title_ru", "title_en", "team__name_ru", "season")
    list_editable = ("price", "stock", "is_active")
    inlines = [ProductImageInline]
    prepopulated_fields = {"slug": ("title_en",)}


@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ("name_ru", "name_en")
    prepopulated_fields = {"slug": ("name_en",)}


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name_ru", "name_en", "league")
    list_filter = ("league",)
    prepopulated_fields = {"slug": ("name_en",)}
