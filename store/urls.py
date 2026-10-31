
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("", views.home, name="home"),
    path("medicines/", views.medicine_list, name="medicine_list"),

    # Shopping cart
    path("cart/", views.cart_detail, name="cart_detail"),
    path(
        "cart/add/<int:listing_id>/",
        views.add_to_cart,
        name="add_to_cart",
    ),
    path(
        "cart/update/<int:listing_id>/",
        views.update_cart,
        name="update_cart",
    ),
    path(
        "cart/remove/<int:listing_id>/",
        views.remove_from_cart,
        name="remove_from_cart",
    ),

    # Customer registration and login
    path("register/", views.register, name="register"),
    path("customer/login/", views.customer_login, name="customer_login"),
    path("vendor/login/", views.vendor_login, name="vendor_login"),
    path("logout/", views.customer_logout, name="logout"),
    path("checkout/", views.checkout, name="checkout"),
    path(
    "order-confirmation/<int:order_id>/",
    views.order_confirmation,
    name="order_confirmation",
    ),
    path("my-orders/", views.order_history, name="order_history"),
    path("vendor/register/", views.vendor_register, name="vendor_register"),
    path("vendor/dashboard/", views.vendor_dashboard, name="vendor_dashboard"),
    path(
    "vendor/medicines/",
    views.vendor_medicines,
    name="vendor_medicines",
),

    path(
    "vendor/listings/add/",
    views.vendor_listing_add,
    name="vendor_listing_add",
),
path(
    "vendor/listings/<int:listing_id>/edit/",
    views.vendor_listing_edit,
    name="vendor_listing_edit",
),
path(
    "vendor/listings/<int:listing_id>/delete/",
    views.vendor_listing_delete,
    name="vendor_listing_delete",
),
path(
    "vendor/orders/<int:item_id>/update/",
    views.vendor_update_order_item,
    name="vendor_update_order_item",
),


    # Admin-only management pages
    path(
        "admin-panel/medicine-approval/",
        views.admin_medicine_approval,
        name="admin_medicine_approval",
    ),
    path(
        "admin-panel/vendor-approval/",
        views.admin_vendor_approval,
        name="admin_vendor_approval",
    ),
    path(
        "admin-panel/vendors/",
        views.admin_vendors_list,
        name="admin_vendors_list",
    ),


    path(
        "admin-panel/vendors/<int:vendor_id>/approve/",
        views.approve_vendor,
        name="approve_vendor",
    ),
    path(
        "admin-panel/medicines/<int:medicine_id>/activate/",
        views.activate_medicine,
        name="activate_medicine",
    ),

    path("admin-login/", views.admin_login, name="admin_login"),

    path(
    "customer/profile/",
    views.customer_profile,
    name="customer_profile",
),
path(
    "customer/profile/",
    views.customer_profile,
    name="customer_profile",
),

path(
    "vendor/profile/",
    views.vendor_profile,
    name="vendor_profile",
),

path(
    "forgot-password/",
    auth_views.PasswordResetView.as_view(
        template_name="store/password_reset_form.html",
        email_template_name="store/password_reset_email.html",
        subject_template_name="store/password_reset_subject.txt",
        success_url="/forgot-password/sent/",
    ),
    name="password_reset",
),
path(
    "forgot-password/sent/",
    auth_views.PasswordResetDoneView.as_view(
        template_name="store/password_reset_done.html",
    ),
    name="password_reset_done",
),
path(
    "reset-password/<uidb64>/<token>/",
    auth_views.PasswordResetConfirmView.as_view(
        template_name="store/password_reset_confirm.html",
        success_url="/reset-password/complete/",
    ),
    name="password_reset_confirm",
),
path(
    "reset-password/complete/",
    auth_views.PasswordResetCompleteView.as_view(
        template_name="store/password_reset_complete.html",
    ),
    name="password_reset_complete",
),


]


