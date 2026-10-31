
from django import forms
from .models import Medicine, VendorListing
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError



class VendorListingForm(forms.ModelForm):
    class Meta:
        model = VendorListing
        fields = [
            "medicine",
            "price",
            "stock_quantity",
            "is_available",
        ]
        widgets = {
            "price": forms.NumberInput(
                attrs={"min": "0.01", "step": "0.01"}
            ),
            "stock_quantity": forms.NumberInput(
                attrs={"min": "0", "step": "1"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["medicine"].queryset = Medicine.objects.filter(
            is_active=True
        ).order_by("name")

    def clean_price(self):
        price = self.cleaned_data["price"]
        if price <= 0:
            raise forms.ValidationError("Price must be greater than zero.")
        return price

    def clean_stock_quantity(self):
        quantity = self.cleaned_data["stock_quantity"]
        if quantity < 0:
            raise forms.ValidationError(
                "Stock quantity cannot be negative."
            )
        return quantity



class VendorMedicineForm(forms.ModelForm):
    category_name = forms.CharField(
        max_length=100,
        label="Medicine Category",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Type or create a category",
            }
        ),
    )

    class Meta:
        model = Medicine
        fields = [
            "name",
            "image",
            "generic_name",
            "description",
            "uses",
            "side_effects",
            "precautions",
            "requires_prescription",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "uses": forms.Textarea(attrs={"rows": 3}),
            "side_effects": forms.Textarea(attrs={"rows": 3}),
            "precautions": forms.Textarea(attrs={"rows": 3}),
        }

class CustomerRegistrationForm(forms.Form):
    display_username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password1 = forms.CharField(
        widget=forms.PasswordInput,
        validators=[validate_password],
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput,
    )
    full_name = forms.CharField(
    max_length=150,
    label="Full Name",
    required=True,
)

    phone = forms.CharField(
    max_length=15,
    label="Phone Number",
    required=True,
)

    def clean_email(self):
        email = self.cleaned_data["email"].strip()

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(
                "An account with this email already exists."
            )

        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Passwords do not match.")

        return cleaned_data