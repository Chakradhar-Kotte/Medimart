
from django.contrib import admin
from .models import (
    Category,
    CustomerProfile,
    VendorProfile,
    Medicine,
    VendorListing,
    Order,
    OrderItem,
)
from django.contrib.auth.models import User

# Show customer and vendor chosen usernames in Django admin
admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        "display_login_username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
    )

    search_fields = ("username", "email", "first_name", "last_name")

    def display_login_username(self, obj):
        customer = CustomerProfile.objects.filter(
            user=obj
        ).first()

        if customer:
            return customer.display_username

        vendor = VendorProfile.objects.filter(
            user=obj
        ).first()

        if vendor:
            return vendor.login_username or obj.username

        return obj.username

    display_login_username.short_description = "USERNAME"
@admin.action(description="Approve selected vendors")
def approve_selected_vendors(modeladmin, request, queryset):
    queryset.update(is_approved=True)


@admin.action(description="Activate selected medicines")
def activate_selected_medicines(modeladmin, request, queryset):
    queryset.update(is_active=True)


@admin.action(description="Deactivate selected medicines")
def deactivate_selected_medicines(modeladmin, request, queryset):
    queryset.update(is_active=False)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    list_display = ("store_name", "user", "phone", "is_approved")
    search_fields = ("store_name", "user__username")
    list_filter = ("is_approved",)
    actions = [approve_selected_vendors]


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "generic_name",
        "requires_prescription",
        "is_active",
    )
    search_fields = ("name", "generic_name")
    list_filter = ("category", "requires_prescription", "is_active")
    actions = [
        activate_selected_medicines,
        deactivate_selected_medicines,
    ]



@admin.register(VendorListing)
class VendorListingAdmin(admin.ModelAdmin):
    list_display = (
        "medicine",
        "vendor",
        "price",
        "stock_quantity",
        "is_available",
    )
    search_fields = ("medicine__name", "vendor__store_name")
    list_filter = ("is_available",)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "total_amount",
        "status",
        "payment_method",
        "created_at",
    )
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("customer__username", "full_name", "phone")
    inlines = [OrderItemInline]