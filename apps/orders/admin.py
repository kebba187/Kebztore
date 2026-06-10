from django.contrib import admin

from .emails import send_order_shipped
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "title", "size", "unit_price", "quantity")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "status", "grand_total", "shipping_method",
                    "tracking_number", "created_at")
    list_filter = ("status", "shipping_method", "created_at")
    search_fields = ("id", "full_name", "email", "phone", "tracking_number")
    # Staff can change status and add a tracking number directly from the list.
    list_editable = ("status", "tracking_number")
    inlines = [OrderItemInline]
    readonly_fields = ("payment_id", "paid_at", "created_at", "updated_at")
    actions = ["mark_shipped", "mark_delivered"]

    @admin.action(description="Отметить как «Отправлен» (+ письмо)")
    def mark_shipped(self, request, queryset):
        sent = skipped = 0
        for order in queryset:
            if not order.tracking_number:
                skipped += 1
                continue
            order.status = Order.Status.SHIPPED
            order.save(update_fields=["status", "updated_at"])
            if send_order_shipped(order):
                sent += 1
        msg = f"Отправлено писем: {sent}."
        if skipped:
            msg += f" Пропущено без трек-номера: {skipped}."
        self.message_user(request, msg)

    @admin.action(description="Отметить как «Доставлен»")
    def mark_delivered(self, request, queryset):
        queryset.update(status=Order.Status.DELIVERED)
