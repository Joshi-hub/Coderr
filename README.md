# Coderr Backend

REST API backend for **Coderr**, a freelancing platform where business users publish service offers, customers place orders, and both sides can exchange reviews.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 6.0 + Django REST Framework |
| Auth | Token Authentication (`rest_framework.authtoken`) |
| Database | SQLite (development) |
| Image handling | Pillow |
| CORS | django-cors-headers |

---

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd coderr-backend
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Apply database migrations

```bash
python manage.py migrate
```

### 5. Seed demo data (optional but recommended)

```bash
python manage.py seed_data
```

This creates two business users, two customer users, demo offers, orders, and reviews.
See **Demo Accounts** section for credentials.

### 6. Create a superuser (optional — for Django Admin)

```bash
python manage.py createsuperuser
```

### 7. Start the development server

```bash
python manage.py runserver
```

The API is now available at `http://127.0.0.1:8000/api/`.

---

## Demo Accounts

All demo accounts use the password `pass123!` except the guest accounts.

| Role | Username | Password |
|---|---|---|
| Business | `kevin_b` | `pass123!` |
| Business | `anna_b` | `pass123!` |
| Customer | `max_k` | `pass123!` |
| Customer | `lisa_m` | `pass123!` |
| **Guest Business** | `kevin` | `asdasd24` |
| **Guest Customer** | `andrey` | `asdasd` |

> The guest accounts are used by the frontend's one-click guest login buttons.

---

## API Endpoints

All endpoints are prefixed with `/api/`.

### Authentication

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `registration/` | None | Register a new user |
| POST | `login/` | None | Log in and receive a token |

### Profiles

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `profile/{id}/` | Required | Retrieve a user profile |
| PATCH | `profile/{id}/` | Owner | Update own profile |
| GET | `profiles/business/` | Required | List all business profiles |
| GET | `profiles/customer/` | Required | List all customer profiles |

### Offers

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `offers/` | None | List all offers (filterable, paginated) |
| POST | `offers/` | Business | Create an offer with 3 typed details |
| GET | `offers/{id}/` | Required | Retrieve a single offer |
| PATCH | `offers/{id}/` | Owner | Update offer fields or details |
| DELETE | `offers/{id}/` | Owner | Delete an offer |
| GET | `offerdetails/{id}/` | Required | Retrieve a single offer detail |

**GET `/api/offers/` query parameters:**

| Parameter | Example | Description |
|---|---|---|
| `creator_id` | `?creator_id=3` | Filter by user ID |
| `min_price` | `?min_price=100` | Minimum starting price |
| `max_delivery_time` | `?max_delivery_time=7` | Maximum delivery days |
| `search` | `?search=logo` | Search in title and description |
| `ordering` | `?ordering=-min_price` | Sort by `min_price`, `updated_at` (prefix `-` for descending) |
| `page_size` | `?page_size=12` | Items per page (default 6) |

### Orders

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `orders/` | Required | List orders the user is involved in |
| POST | `orders/` | Customer | Create an order from an `offer_detail_id` |
| PATCH | `orders/{id}/` | Business owner | Update order status |
| DELETE | `orders/{id}/` | Staff | Delete an order |
| GET | `order-count/{user_id}/` | Required | Active order count for a business user |
| GET | `completed-order-count/{user_id}/` | Required | Completed order count for a business user |

### Reviews

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `reviews/` | Required | List all reviews (filterable) |
| POST | `reviews/` | Customer | Create a review (one per business user) |
| PATCH | `reviews/{id}/` | Reviewer | Update rating or description |
| DELETE | `reviews/{id}/` | Reviewer | Delete a review |

**GET `/api/reviews/` query parameters:**

| Parameter | Description |
|---|---|
| `business_user_id` | Filter by business user |
| `reviewer_id` | Filter by reviewer |
| `ordering` | Sort by `rating` or `updated_at` (prefix `-` for descending) |

### Platform Stats

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `base-info/` | None | Public platform statistics |

---

## Project Structure

```
coderr-backend/
├── core/               # Django project settings, root URL config
├── auth_app/           # Registration and login endpoints
├── profiles_app/       # User profiles (business / customer)
├── offers_app/         # Offers and offer details
├── orders_app/         # Orders placed by customers
├── reviews_app/        # Reviews left by customers
└── base_app/           # Public platform stats + seed data management command
```

Each app follows the convention:

```
<app>/
├── api/
│   ├── permissions.py
│   ├── serializers.py
│   ├── urls.py
│   └── views.py
├── migrations/
├── admin.py
├── models.py
└── tests.py
```

---

## Notes

- `db.sqlite3` is excluded from version control via `.gitignore`.
- Media files (profile images, offer images) are stored locally in `media/` during development.
- To reset the database and reseed: delete `db.sqlite3`, run `migrate`, then `seed_data`.
