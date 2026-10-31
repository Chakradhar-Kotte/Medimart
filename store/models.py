
from django.conf import settings
from django.db import models
from decimal import Decimal


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name



class VendorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    login_username = models.CharField(
    max_length=150,
    null=True,
    blank=True
    )
    store_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return self.store_name

class Medicine(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="medicines"
    )
    name = models.CharField(max_length=150)
    image = models.ImageField(
        upload_to="medicines/",
        blank=True,
        null=True
    )
    generic_name = models.CharField(max_length=150, blank=True)
    description = models.TextField()
    uses = models.TextField()
    side_effects = models.TextField(blank=True)
    precautions = models.TextField(blank=True)
    requires_prescription = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class VendorListing(models.Model):
    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.CASCADE,
        related_name="listings"
    )
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.CASCADE,
        related_name="vendor_listings"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["vendor", "medicine"],
                name="unique_vendor_medicine_listing"
            )
        ]

    def __str__(self):
        return f"{self.medicine.name} - {self.vendor.store_name}"


from decimal import Decimal


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]
    customer_order_number = models.PositiveIntegerField(
    null=True,
    blank=True
    )

    PAYMENT_CHOICES = [
        ("cod", "Cash on Delivery"),
        ("online", "Online Payment"),
    ]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="medimart_orders",
    )
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15)
    delivery_address = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_CHOICES,
        default="cod",
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.pk} - {self.customer}"


class OrderItem(models.Model):
    STATUS_CHOICES = [
        ("pending", "New Request"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("processing", "Processing"),
        ("completed", "Completed"),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    vendor = models.ForeignKey(
        VendorProfile,
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    def __str__(self):
        return f"{self.medicine.name} x {self.quantity}"


customer_order_number = models.PositiveIntegerField(
    null=True,
    blank=True,
)

from django.conf import settings
from django.db import models



class CustomerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customerprofile",
    )
    display_username = models.CharField(max_length=150)
    full_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    delivery_address = models.TextField(blank=True)

    def __str__(self):
        return self.display_username
