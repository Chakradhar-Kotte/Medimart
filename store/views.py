
from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth import login,logout,authenticate,update_session_auth_hash
from django.contrib.auth.forms import UserCreationForm,AuthenticationForm
from django.db.models import Q, Prefetch
from django.contrib import messages
from decimal import Decimal,InvalidOperation
from django.contrib.auth.decorators import login_required,user_passes_test
from django.db import transaction
from django.views.decorators.http import require_POST
from .models import Category, Medicine, VendorListing, VendorProfile,Order,OrderItem
from .forms import VendorListingForm, VendorMedicineForm
from django.db.models import F
from django.contrib.auth.models import User
from .forms import CustomerRegistrationForm
from .models import CustomerProfile
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.mail import send_mail
from math import radians, sin, cos, sqrt, atan2

def home(request):
    return render(request, "store/home.html")

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two locations in kilometers.
    """
    earth_radius = 6371

    lat1 = radians(float(lat1))
    lon1 = radians(float(lon1))
    lat2 = radians(float(lat2))
    lon2 = radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return earth_radius * c


def medicine_list(request):
    query = request.GET.get("q", "").strip()

    available_listings = (
        VendorListing.objects
        .filter(
            is_available=True,
            stock_quantity__gt=0,
            vendor__is_approved=True,
        )
        .select_related("vendor")
        .order_by("price")
    )

    medicines = (
        Medicine.objects
        .filter(
            is_active=True,
            vendor_listings__is_available=True,
            vendor_listings__stock_quantity__gt=0,
            vendor_listings__vendor__is_approved=True,
        )
        .select_related("category")
        .prefetch_related(
            Prefetch(
                "vendor_listings",
                queryset=available_listings,
                to_attr="available_listings",
            )
        )
        .distinct()
        .order_by("name")
    )

    if query:
        medicines = medicines.filter(
            Q(name__icontains=query)
            | Q(generic_name__icontains=query)
            | Q(category__name__icontains=query)
        )

    # Get approved vendors who have saved store coordinates.
    nearby_stores = (
        VendorProfile.objects
        .filter(
            is_approved=True,
            latitude__isnull=False,
            longitude__isnull=False,
        )
        .exclude(address="")
    )

    customer_lat = request.GET.get("latitude")
    customer_lng = request.GET.get("longitude")

    stores_with_distance = []

    if customer_lat and customer_lng:
        try:
            customer_lat = float(customer_lat)
            customer_lng = float(customer_lng)

            if not (-90 <= customer_lat <= 90 and
                    -180 <= customer_lng <= 180):
                raise ValueError("Invalid coordinates")

            for store in nearby_stores:
                distance = calculate_distance(
                    customer_lat,
                    customer_lng,
                    store.latitude,
                    store.longitude,
                )

                stores_with_distance.append({
                    "store": store,
                    "distance": round(distance, 2),
                })

            stores_with_distance.sort(
                key=lambda item: item["distance"]
            )

        except (ValueError, TypeError):
            stores_with_distance = []

    context = {
        "medicines": medicines,
        "query": query,
        "nearby_stores": stores_with_distance,
    }

    return render(request, "store/medicine_list.html", context)
from decimal import Decimal

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import VendorListing


def cart_detail(request):
    cart = request.session.get("cart", {})
    cart_items = []
    total = Decimal("0.00")

    for listing_id, quantity in cart.items():
        try:
            listing = VendorListing.objects.select_related(
                "medicine", "vendor"
            ).get(
                pk=int(listing_id),
                is_available=True,
                stock_quantity__gt=0,
                vendor__is_approved=True,
                medicine__is_active=True,
            )

            quantity = int(quantity)
            if quantity < 1:
                continue

            quantity = min(quantity, listing.stock_quantity)
            subtotal = listing.price * quantity

            cart_items.append({
                "listing": listing,
                "quantity": quantity,
                "subtotal": subtotal,
            })
            total += subtotal

        except (VendorListing.DoesNotExist, ValueError, TypeError):
            continue

    return render(request, "store/cart.html", {
        "cart_items": cart_items,
        "total": total,
    })


@require_POST
def add_to_cart(request, listing_id):
    listing = get_object_or_404(
        VendorListing,
        pk=listing_id,
        is_available=True,
        stock_quantity__gt=0,
        vendor__is_approved=True,
        medicine__is_active=True,
    )

    cart = request.session.get("cart", {})
    key = str(listing.id)

    try:
        current_quantity = int(cart.get(key, 0))
    except (ValueError, TypeError):
        current_quantity = 0

    if current_quantity >= listing.stock_quantity:
        messages.warning(request, "You have reached the available stock limit.")
    else:
        cart[key] = current_quantity + 1
        request.session["cart"] = cart
        messages.success(request, f"{listing.medicine.name} added to your cart.")

    return redirect("cart_detail")


@require_POST
def update_cart(request, listing_id):
    listing = get_object_or_404(VendorListing, pk=listing_id)
    cart = request.session.get("cart", {})
    key = str(listing.id)

    try:
        quantity = int(request.POST.get("quantity", "1"))
    except (ValueError, TypeError):
        quantity = 1

    if quantity <= 0:
        cart.pop(key, None)
    elif (
        listing.is_available
        and listing.vendor.is_approved
        and listing.medicine.is_active
    ):
        cart[key] = min(quantity, listing.stock_quantity)
    else:
        cart.pop(key, None)

    request.session["cart"] = cart
    messages.success(request, "Your cart has been updated.")
    return redirect("cart_detail")


@require_POST
def remove_from_cart(request, listing_id):
    cart = request.session.get("cart", {})
    key = str(listing_id)

    if key in cart:
        cart.pop(key)
        request.session["cart"] = cart
        messages.success(request, "Item removed from your cart.")
    else:
        messages.info(request, "That item was already removed from your cart.")

    return redirect("cart_detail")

def register(request):
    if request.method == "POST":
        form = CustomerRegistrationForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"].strip()
            display_username = form.cleaned_data["display_username"].strip()
            full_name = form.cleaned_data["full_name"].strip()
            phone = form.cleaned_data["phone"].strip()
            password = form.cleaned_data["password1"]
            
            # Generate a unique internal Django username.
            base_username = "customer"
            username = base_username
            counter = 1

            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                )

                CustomerProfile.objects.create(
    user=user,
    display_username=display_username,
    full_name=full_name,
    phone=phone,
)

            messages.success(
                request,
                "Registration successful! Please log in with your email."
            )
            return redirect("customer_login")
    else:
        form = CustomerRegistrationForm()

    return render(
        request,
        "store/register.html",
        {"form": form},
    )


def vendor_register(request):
    User = get_user_model()

    if request.method == "POST":
        login_username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        store_name = request.POST.get("store_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()

        if not all([
            login_username, email, password1, password2,
            store_name, phone, address
        ]):
            messages.error(request, "Please fill in all fields.")

        elif User.objects.filter(email__iexact=email).exists():
            messages.error(
                request,
                "This email address is already registered. Please use another email."
            )

        elif password1 != password2:
            messages.error(request, "The passwords do not match.")

        else:
            try:
                validate_password(password1)
            except ValidationError as error:
                for message in error.messages:
                    messages.error(request, message)
            else:
                try:
                    with transaction.atomic():
                        # Generate an internal username that is always unique.
                        number = 1
                        internal_username = f"vendor_account_{number}"

                        while User.objects.filter(
                            username=internal_username
                        ).exists():
                            number += 1
                            internal_username = f"vendor_account_{number}"

                        user = User.objects.create_user(
                            username=internal_username,
                            email=email,
                            password=password1,
                        )

                        VendorProfile.objects.create(
                            user=user,
                            login_username=login_username,
                            store_name=store_name,
                            phone=phone,
                            address=address,
                            is_approved=False,
                        )

                    messages.success(
                        request,
                        "Vendor registration successful! Please wait for admin approval."
                    )
                    return redirect("vendor_login")

                except Exception:
                    messages.error(
                        request,
                        "Registration could not be completed. Please check the details and try again."
                    )

    return render(request, "store/vendor_register.html")

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User


def customer_login(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        matching_users = User.objects.filter(
            email__iexact=email
        )

        if matching_users.count() != 1:
            messages.error(
                request,
                "Invalid email or password."
            )
        else:
            user_record = matching_users.first()

            if VendorProfile.objects.filter(user=user_record).exists():
                messages.error(
                    request,
                    "Please use the Vendor Login page."
                )
            else:
                user = authenticate(
                    request,
                    username=user_record.username,
                    password=password,
                )

                if user is not None:
                    login(request, user)
                    messages.success(
                        request,
                        "Customer login successful!"
                    )
                    return redirect("home")

                messages.error(
                    request,
                    "Invalid email or password."
                )

    return render(request, "store/customer_login.html")



@require_POST
def customer_logout(request):
    logout(request)
    messages.success(request, "You have logged out successfully.")
    return redirect("home")

@login_required
def checkout(request):
    cart = request.session.get("cart", {})

    if not request.user.is_authenticated:
        messages.info(
            request,
            "Please register or log in to your MediMart account "
            "to proceed with your order. Your cart items will be "
            "waiting for you after you sign in."
        )
        return redirect("customer_login")

    if not cart:
        messages.error(request, "Your cart is empty.")
        return redirect("cart_detail")

    cart_items = []
    total = Decimal("0.00")

    for listing_id, quantity in cart.items():
        try:
            quantity = int(quantity)

            if quantity < 1:
                raise ValueError

            listing = VendorListing.objects.select_related(
                "medicine", "vendor"
            ).get(
                pk=int(listing_id),
                is_available=True,
                vendor__is_approved=True,
                medicine__is_active=True,
            )

            if quantity > listing.stock_quantity:
                messages.error(
                    request,
                    f"Not enough stock for {listing.medicine.name}.",
                )
                return redirect("cart_detail")

            subtotal = listing.price * quantity

            cart_items.append({
                "listing": listing,
                "quantity": quantity,
                "subtotal": subtotal,
            })

            total += subtotal

        except (
            VendorListing.DoesNotExist,
            ValueError,
            TypeError,
        ):
            messages.error(
                request,
                "An item in your cart is no longer available.",
            )
            return redirect("cart_detail")

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("delivery_address", "").strip()

        if not full_name or not phone or not address:
            messages.error(
                request,
                "Please fill in all delivery details.",
            )
            return render(
                request,
                "store/checkout.html",
                {
                    "cart_items": cart_items,
                    "total": total,
                },
            )

        if len(full_name) > 150 or len(phone) > 15:
            messages.error(
                request,
                "Please check your name and phone number.",
            )
            return render(
                request,
                "store/checkout.html",
                {
                    "cart_items": cart_items,
                    "total": total,
                },
            )

        try:
            with transaction.atomic():
                # Lock this customer's existing orders while
                # calculating the next customer-specific number.
                last_order = (
                    Order.objects.select_for_update()
                    .filter(customer=request.user)
                    .exclude(customer_order_number__isnull=True)
                    .order_by("-customer_order_number")
                    .first()
                )

                next_order_number = (
                    last_order.customer_order_number + 1
                    if last_order
                    else 1
                )

                order = Order.objects.create(
                    customer=request.user,
                    customer_order_number=next_order_number,
                    full_name=full_name,
                    phone=phone,
                    delivery_address=address,
                    payment_method="cod",
                    total_amount=Decimal("0.00"),
                )

                confirmed_total = Decimal("0.00")

                for item in cart_items:
                    listing = (
                        VendorListing.objects.select_for_update()
                        .select_related("medicine", "vendor")
                        .get(pk=item["listing"].pk)
                    )

                    quantity = item["quantity"]

                    if (
                        not listing.is_available
                        or not listing.vendor.is_approved
                        or not listing.medicine.is_active
                        or listing.stock_quantity < quantity
                    ):
                        raise ValueError(
                            f"Stock or availability changed for "
                            f"{listing.medicine.name}."
                        )

                    unit_price = listing.price
                    subtotal = unit_price * quantity

                    OrderItem.objects.create(
                        order=order,
                        vendor=listing.vendor,
                        medicine=listing.medicine,
                        quantity=quantity,
                        unit_price=unit_price,
                        subtotal=subtotal,
                    )

                    listing.stock_quantity -= quantity
                    listing.save(update_fields=["stock_quantity"])

                    confirmed_total += subtotal

                order.total_amount = confirmed_total
                order.save(update_fields=["total_amount"])

        except (ValueError, VendorListing.DoesNotExist):
            messages.error(
                request,
                "Your order could not be completed because an item changed. "
                "Please review your cart and try again.",
            )
            return redirect("cart_detail")

        request.session["cart"] = {}
        request.session.modified = True
        
        # Send an email to each vendor for their own ordered items.
        vendor_items = {}

        order_items = OrderItem.objects.filter(
            order=order
        ).select_related("vendor__user", "medicine")

        for order_item in order_items:
            vendor = order_item.vendor

            if vendor.id not in vendor_items:
                vendor_items[vendor.id] = {
                    "vendor": vendor,
                    "items": [],
                }

            vendor_items[vendor.id]["items"].append(order_item)

        for vendor_data in vendor_items.values():
            vendor = vendor_data["vendor"]
            recipient_email = vendor.user.email.strip()
            print("VENDOR STORE:", vendor.store_name)
            print("VENDOR EMAIL:", repr(recipient_email))

            if not recipient_email:
                continue

            item_lines = []
            for order_item in vendor_data["items"]:
                item_lines.append(
                    f"- {order_item.medicine.name} | "
                    f"Quantity: {order_item.quantity} | "
                    f"Subtotal: Rs. {order_item.subtotal}"
                )

            email_subject = (
                f"MediMart: New Order #{order.customer_order_number}"
            )

            email_message = (
                f"Hello {vendor.store_name},\n\n"
                f"You have received a new order through MediMart.\n\n"
                f"Order number: #{order.customer_order_number}\n"
                f"Customer: {order.full_name}\n"
                f"Customer phone: {order.phone}\n"
                f"Delivery address: {order.delivery_address}\n\n"
                f"Your ordered medicines:\n"
                + "\n".join(item_lines)
                + f"\n\nYour items total: Rs. "
                + str(
                    sum(
                        (item.subtotal for item in vendor_data["items"]),
                        Decimal("0.00"),
                    )
                )
                + "\n\nPlease log in to your MediMart Vendor Dashboard "
                  "to manage this order.\n"
            )

            try:
                send_mail(
                    email_subject,
                    email_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [recipient_email],
                    fail_silently=False,
                )
            except Exception:
                # Email failure must not undo a successfully placed order.
                import logging
                logging.getLogger(__name__).exception(
                    "Could not send order notification to vendor ID %s",
                    vendor.id,
                )


        messages.success(
            request,
            f"Order #{order.customer_order_number} placed successfully!",
        )

        return redirect(
            "order_confirmation",
            order_id=order.pk,
        )

    return render(
        request,
        "store/checkout.html",
        {
            "cart_items": cart_items,
            "total": total,
        },
    )


@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(
        Order,
        pk=order_id,
        customer=request.user,
    )

    return render(
        request,
        "store/order_confirmation.html",
        {"order": order},
    )

@login_required
def order_history(request):
    # Get only orders placed by the currently logged-in customer
    orders = (
        Order.objects
        .filter(customer_id=request.user.id)
        .prefetch_related("items__medicine", "items__vendor")
        .order_by("-created_at", "-id")
    )

    return render(
        request,
        "store/order_history.html",
        {"orders": orders},
    )





@login_required
def vendor_dashboard(request):
    vendor = VendorProfile.objects.filter(user=request.user).first()

    if vendor is None:
        messages.error(request, "You do not have a vendor account.")
        return redirect("vendor_login")

    if not vendor.is_approved:
        messages.error(
            request,
            "Your vendor account is waiting for admin approval."
        )
        return redirect("vendor_login")

    listings = (
        VendorListing.objects.filter(vendor=vendor)
        .select_related("medicine", "medicine__category")
        .order_by("medicine__name")
    )

    available_count = listings.filter(
        is_available=True,
        stock_quantity__gt=0,
        medicine__is_active=True
    ).count()

    # Only show order items assigned to this vendor.
    order_items = (
        OrderItem.objects.filter(vendor=vendor)
        .select_related("order", "order__customer", "medicine")
        .order_by("-order__created_at")
    )

    order_counts = {
        "pending": order_items.filter(status="pending").count(),
        "accepted": order_items.filter(status="accepted").count(),
        "rejected": order_items.filter(status="rejected").count(),
        "processing": order_items.filter(status="processing").count(),
        "completed": order_items.filter(status="completed").count(),
    }

    return render(
        request,
        "store/vendor_dashboard.html",
        {
            "vendor": vendor,
            "listings": listings,
            "available_count": available_count,
            "order_items": order_items,
            "order_counts": order_counts,
        }
    )
@login_required
def vendor_order_requests(request):
    vendor = VendorProfile.objects.filter(user=request.user).first()

    if vendor is None:
        messages.error(request, "You do not have a vendor account.")
        return redirect("vendor_login")

    if not vendor.is_approved:
        messages.error(
            request,
            "Your vendor account is waiting for admin approval."
        )
        return redirect("vendor_login")

    order_items = (
        OrderItem.objects.filter(vendor=vendor)
        .select_related("order", "order__customer", "medicine")
        .order_by("-order__created_at")
    )

    return render(
        request,
        "store/vendor_order_requests.html",
        {
            "vendor": vendor,
            "order_items": order_items,
        }
    )
@login_required
@require_POST
def vendor_update_order_item(request, item_id):
    vendor = VendorProfile.objects.filter(
        user=request.user,
        is_approved=True,
    ).first()

    if vendor is None:
        messages.error(request, "Approved vendor account required.")
        return redirect("vendor_login")

    item = get_object_or_404(
        OrderItem,
        pk=item_id,
        vendor=vendor,
    )

    action = request.POST.get("action")

    allowed_transitions = {
        "accept": ("pending", "accepted"),
        "reject": ("pending", "rejected"),
        "processing": ("accepted", "processing"),
        "complete": ("processing", "completed"),
    }

    transition = allowed_transitions.get(action)

    if transition is None:
        messages.error(request, "Invalid order action.")

    elif item.status != transition[0]:
        messages.error(
            request,
            "This order item has already changed status. Please refresh."
        )

    else:
        try:
            with transaction.atomic():
                # Lock the order item to prevent duplicate updates.
                item = OrderItem.objects.select_for_update().get(
                    pk=item_id,
                    vendor=vendor,
                )

                if item.status != transition[0]:
                    messages.error(
                        request,
                        "This order item has already changed status. "
                        "Please refresh."
                    )
                    return redirect("vendor_dashboard")

                # Restore stock if the vendor rejects this item.
                if action == "reject":
                    listing = VendorListing.objects.select_for_update().filter(
                        vendor=vendor,
                        medicine=item.medicine,
                    ).first()

                    if listing is None:
                        raise VendorListing.DoesNotExist

                    listing.stock_quantity = (
                        F("stock_quantity") + item.quantity
                    )
                    listing.save(update_fields=["stock_quantity"])

                # Update the individual order item.
                item.status = transition[1]
                item.save(update_fields=["status"])

                # Recalculate the overall order status.
                item_statuses = list(
                    OrderItem.objects.filter(
                        order=item.order
                    ).values_list("status", flat=True)
                )

                if item_statuses and all(
                    status == "rejected"
                    for status in item_statuses
                ):
                    overall_status = "cancelled"

                elif item_statuses and all(
                    status in ("completed", "rejected")
                    for status in item_statuses
                ):
                    overall_status = (
                        "delivered"
                        if "completed" in item_statuses
                        else "cancelled"
                    )

                elif "processing" in item_statuses:
                    overall_status = "processing"

                elif "accepted" in item_statuses:
                    overall_status = "confirmed"

                else:
                    overall_status = "pending"

                item.order.status = overall_status
                item.order.save(update_fields=["status"])

            messages.success(
                request,
                f"{item.medicine.name}: status updated to "
                f"{item.get_status_display()}."
            )

        except VendorListing.DoesNotExist:
            messages.error(
                request,
                "Could not find this vendor's medicine listing. "
                "The order update was not saved."
            )

    return redirect("vendor_dashboard")


@login_required
def vendor_listing_add(request):
    vendor = VendorProfile.objects.filter(
        user=request.user
    ).first()

    if vendor is None:
        messages.error(
            request,
            "You do not have a vendor account."
        )
        return redirect("vendor_login")

    if not vendor.is_approved:
        messages.error(
            request,
            "Your vendor account is waiting for admin approval."
        )
        return redirect("vendor_login")

    if request.method == "POST":
        form = VendorMedicineForm(
    request.POST,
    request.FILES
)

        price = request.POST.get("price", "")
        stock_quantity = request.POST.get("stock_quantity", "")

        if form.is_valid():
            try:
                price_value = Decimal(price)
                stock_value = int(stock_quantity)

                if price_value <= 0:
                    raise ValueError

                if stock_value < 0:
                    raise ValueError

            except (ValueError, InvalidOperation):
                messages.error(
                    request,
                    "Enter a valid price greater than zero and "
                    "a stock quantity of zero or more."
                )
                return render(
                    request,
                    "store/vendor_listing_form.html",
                    {
                        "form": form,
                        "is_new_medicine": True,
                    }
                )

            category_name = form.cleaned_data[
                "category_name"
            ].strip()

            if not category_name:
                form.add_error(
                    "category_name",
                    "Please enter a medicine category."
                )
                return render(
                    request,
                    "store/vendor_listing_form.html",
                    {
                        "form": form,
                        "is_new_medicine": True,
                    }
                )

            category, created = Category.objects.get_or_create(
                name__iexact=category_name,
                defaults={"name": category_name},
            )

            medicine = form.save(commit=False)
            medicine.category = category

            # Newly submitted medicines require admin review.
            medicine.is_active = False
            medicine.save()

            VendorListing.objects.create(
                vendor=vendor,
                medicine=medicine,
                price=price_value,
                stock_quantity=stock_value,
                is_available=True,
            )

            messages.success(
                request,
                "Medicine submitted successfully. "
                "An admin must approve it before customers can buy it."
            )
            return redirect("vendor_dashboard")

    else:
        form = VendorMedicineForm()

    return render(
        request,
        "store/vendor_listing_form.html",
        {
            "form": form,
            "is_new_medicine": True,
        }
    )



@login_required
def vendor_listing_edit(request, listing_id):
    vendor = VendorProfile.objects.filter(user=request.user).first()

    if vendor is None or not vendor.is_approved:
        messages.error(request, "Your approved vendor account is required.")
        return redirect("vendor_login")

    # Vendors can edit only their own listings.
    listing = get_object_or_404(
        VendorListing,
        id=listing_id,
        vendor=vendor,
    )

    if request.method == "POST":
        form = VendorMedicineForm(
    request.POST,
    request.FILES,
    instance=listing.medicine,
)

        try:
            price_value = Decimal(request.POST.get("price", ""))
            stock_value = int(request.POST.get("stock_quantity", ""))

            if price_value <= 0 or stock_value < 0:
                raise ValueError

        except (ValueError, InvalidOperation):
            messages.error(
                request,
                "Enter a price greater than zero and a stock quantity "
                "of zero or more."
            )
            return render(
                request,
                "store/vendor_listing_form.html",
                {
                    "form": form,
                    "listing": listing,
                    "is_new_medicine": False,
                },
            )

        if form.is_valid():
            medicine = form.save(commit=False)

            # Medicine details need admin review after editing.
            medicine.is_active = False
            medicine.save()

            listing.price = price_value
            listing.stock_quantity = stock_value
            listing.is_available = True
            listing.save()

            messages.success(
                request,
                "Medicine details updated. Admin approval is required "
                "before this medicine is available to customers again."
            )
            return redirect("vendor_dashboard")

    else:
        form = VendorMedicineForm(instance=listing.medicine)

    return render(
        request,
        "store/vendor_listing_form.html",
        {
            "form": form,
            "listing": listing,
            "is_new_medicine": False,
        },
    )


@login_required
@require_POST
def vendor_listing_delete(request, listing_id):
    vendor = VendorProfile.objects.filter(
        user=request.user,
        is_approved=True
    ).first()

    if vendor is None:
        messages.error(request, "You need an approved vendor account.")
        return redirect("vendor_login")

    listing = get_object_or_404(
        VendorListing,
        id=listing_id,
        vendor=vendor
    )

    listing.delete()
    messages.success(request, "Medicine listing deleted.")
    return redirect("vendor_dashboard")


@login_required
def vendor_listing_add_placeholder(request):
    # Not used. Do not call this function.
    return redirect("vendor_dashboard")



@login_required
def vendor_medicines(request):
    vendor = VendorProfile.objects.filter(user=request.user).first()

    if vendor is None:
        messages.error(
            request,
            "This account is not registered as a vendor."
        )
        return redirect("home")

    if not vendor.is_approved:
        messages.warning(
            request,
            "Your vendor account is waiting for admin approval."
        )
        return redirect("vendor_login")

    listings = (
        VendorListing.objects
        .filter(vendor=vendor)
        .select_related("medicine", "medicine__category")
        .order_by("medicine__name")
    )

    available_count = listings.filter(
        is_available=True,
        stock_quantity__gt=0,
        medicine__is_active=True
    ).count()

    return render(
        request,
        "store/vendor_medicines.html",
        {
            "vendor": vendor,
            "listings": listings,
            "available_count": available_count,
        },
    )

def vendor_login(request):
    if request.method == "POST":
        login_username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        print("VENDOR LOGIN POST RECEIVED")
        print("Username entered:", login_username)
        print("Email entered:", email)

        vendor = VendorProfile.objects.select_related("user").filter(
            login_username__iexact=login_username,
            user__email__iexact=email,
        ).first()

        if vendor is None:
            print("LOGIN FAILED: vendor username/email not found")
            messages.error(
                request,
                "Invalid username, email, or password."
            )

        else:
            print("Vendor profile found")
            print("Vendor approved:", vendor.is_approved)

            user = authenticate(
                request,
                username=vendor.user.username,
                password=password,
            )

            if user is None:
                print("LOGIN FAILED: password authentication failed")
                messages.error(
                    request,
                    "Invalid username, email, or password."
                )

            elif not vendor.is_approved:
                print("LOGIN FAILED: vendor is not approved")
                messages.error(
                    request,
                    "Your vendor account is awaiting approval."
                )

            else:
                login(request, user)
                messages.success(request, "Vendor login successful!")
                print("VENDOR LOGIN SUCCESSFUL")
                return redirect("home")

    return render(request, "store/vendor_login.html")



def admin_medicine_approval(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "Admin access is required.")
        return redirect("home")

    medicines = Medicine.objects.select_related("category").all().order_by("name")

    return render(
        request,
        "store/admin_medicine_approval.html",
        {"medicines": medicines},
    )


def admin_vendor_approval(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "Admin access is required.")
        return redirect("home")

    vendors = VendorProfile.objects.select_related("user").filter(
        is_approved=False
    ).order_by("store_name")

    return render(
        request,
        "store/admin_vendor_approval.html",
        {"vendors": vendors},
    )


def admin_vendors_list(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "Admin access is required.")
        return redirect("home")

    vendors = VendorProfile.objects.select_related("user").all().order_by(
        "store_name"
    )

    return render(
        request,
        "store/admin_vendors_list.html",
        {"vendors": vendors},
    )


from django.views.decorators.http import require_POST


@require_POST
def approve_vendor(request, vendor_id):
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "Admin access is required.")
        return redirect("home")

    vendor = get_object_or_404(VendorProfile, pk=vendor_id)
    vendor.is_approved = True
    vendor.save(update_fields=["is_approved"])

    messages.success(request, f"{vendor.store_name} has been approved.")
    return redirect("admin_vendor_approval")


@require_POST
def activate_medicine(request, medicine_id):
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "Admin access is required.")
        return redirect("home")

    medicine = get_object_or_404(Medicine, pk=medicine_id)
    medicine.is_active = True
    medicine.save(update_fields=["is_active"])

    messages.success(request, f"{medicine.name} has been activated.")
    return redirect("admin_medicine_approval")


def admin_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None and user.is_superuser:
            login(request, user)
            messages.success(request, "Admin login successful!")
            return redirect("home")

        messages.error(
            request,
            "Invalid admin username or password.",
        )

    return render(request, "store/admin_login.html")


@login_required
def customer_profile(request):
    if VendorProfile.objects.filter(user=request.user).exists():
        messages.error(request, "Please use the Vendor Dashboard.")
        return redirect("home")

    profile, created = CustomerProfile.objects.get_or_create(
        user=request.user,
        defaults={
            "display_username": request.user.username,
        },
    )

    if request.method == "POST":
        display_username = request.POST.get(
            "display_username", ""
        ).strip()
        email = request.POST.get("email", "").strip()
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        delivery_address = request.POST.get(
            "delivery_address", ""
        ).strip()

        if not all([display_username, email, full_name, phone, delivery_address]):
            messages.error(request, "Please fill in all profile fields.")
            return render(
                request,
                "store/customer_profile.html",
                {"profile": profile, "editing": True},
            )

        if User.objects.filter(
            email__iexact=email
        ).exclude(pk=request.user.pk).exists():
            messages.error(request, "That email is already in use.")
            return render(
                request,
                "store/customer_profile.html",
                {"profile": profile, "editing": True},
            )

        profile.display_username = display_username
        profile.full_name = full_name
        profile.phone = phone
        profile.delivery_address = delivery_address
        profile.save()

        request.user.email = email
        request.user.save(update_fields=["email"])

        messages.success(request, "Your profile was updated successfully.")
        return redirect("customer_profile")

    editing = request.GET.get("edit") == "1"

    return render(
        request,
        "store/customer_profile.html",
        {"profile": profile, "editing": editing},
    )


@login_required
def vendor_profile(request):
    vendor = VendorProfile.objects.filter(
        user=request.user
    ).first()

    if vendor is None:
        messages.error(
            request,
            "This account is not registered as a vendor."
        )
        return redirect("home")

    if request.method == "POST":
        login_username = request.POST.get(
            "login_username", ""
        ).strip()
        store_name = request.POST.get(
            "store_name", ""
        ).strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()

        latitude_value = request.POST.get("latitude", "").strip()
        longitude_value = request.POST.get("longitude", "").strip()

        if not all([login_username, store_name, phone, address]):
            messages.error(
                request,
                "Please fill in all vendor profile fields."
            )
            return render(
                request,
                "store/vendor_profile.html",
                {
                    "vendor": vendor,
                    "editing": True,
                },
            )

        # Validate the coordinates if provided
        try:
            latitude = float(latitude_value) if latitude_value else None
            longitude = float(longitude_value) if longitude_value else None

            if latitude is not None and not -90 <= latitude <= 90:
                raise ValueError

            if longitude is not None and not -180 <= longitude <= 180:
                raise ValueError

            if (latitude is None) != (longitude is None):
                raise ValueError

        except ValueError:
            messages.error(
                request,
                "Please select a valid store location on the map."
            )
            return render(
                request,
                "store/vendor_profile.html",
                {
                    "vendor": vendor,
                    "editing": True,
                },
            )

        vendor.login_username = login_username
        vendor.store_name = store_name
        vendor.phone = phone
        vendor.address = address
        vendor.latitude = latitude
        vendor.longitude = longitude

        vendor.save()

        messages.success(
            request,
            "Vendor profile updated successfully."
        )
        return redirect("vendor_profile")

    editing = request.GET.get("edit") == "1"

    return render(
        request,
        "store/vendor_profile.html",
        {
            "vendor": vendor,
            "editing": editing,
        },
    )
