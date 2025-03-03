# Coderr - Backend Project

This is a practice project as part of the Backend Developer training at **Developer Akademie**.  
The project is a backend system developed using Django Rest Framework (DRF) and serves as an API for handling offers, orders, reviews, and user management.

Frontend: Coderr_frontend_v1.1.0

## 🚀 Features
- **User Authentication**: Registration, login, and role-based access.
- **Profile Management**: Customers and business users with different permissions.
- **Offer System**: Businesses can create offers with detailed packages.
- **Order Management**: Customers can place orders, and businesses can manage them.
- **Review System**: Customers can leave reviews for business users.
- **Filtering & Sorting**: API endpoints support filtering, ordering, and pagination.
- **File Upload**: Profile pictures and offer images.

---

## 🛠️ Technologies Used
- **Django** - Python web framework
- **Django Rest Framework (DRF)** - API development
- **SQLite3** - Database
- **Docker** - Containerization (optional)
- **Token Authentification** - Secure user authentication
- **CORS Middleware** - Allow frontend to interact with the backend

---

## ⚙️ Installation & Setup

### 1️⃣ **Clone the Repository**
```bash
git clone https://github.com/Dogan36/coderr-backend.git
cd coderr-backend
```

### 2️⃣ **Create and Activate Virtual Environment**
```bash
python -m venv env
source env/bin/activate  # Mac/Linux
env\Scripts\activate     # Windows
```

### 3️⃣ **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 4️⃣ **Set Up the Database**
```bash
python manage.py migrate
```

### 5️⃣ **Create a Superuser (Admin)**
```bash
python manage.py createsuperuser
```

### 6️⃣ **Run the Development Server**
```bash
python manage.py runserver
```

The API will be available at:  
🔗 **http://127.0.0.1:8000/api/**

---

## 📚 API Endpoints

### 🛥️ **Authentication**
| Method | Endpoint | Description |
|--------|---------|------------|
| `POST` | `/api/register/` | Register a new user |
| `POST` | `/api/login/` | User login |
| `GET` | `/api/profile/{id}/` | Get user profile |
| `PATCH` | `/api/profile/{id}/` | Update user profile |

### 🛥️ **Offers**
| Method | Endpoint | Description |
|--------|---------|------------|
| `GET` | `/api/offers/` | List all offers |
| `POST` | `/api/offers/` | Create a new offer (business users only) |
| `GET` | `/api/offers/{id}/` | Retrieve offer details |
| `PATCH` | `/api/offers/{id}/` | Update an offer |
| `DELETE` | `/api/offers/{id}/` | Delete an offer (admin only) |

### 🛥️ **Orders**
| Method | Endpoint | Description |
|--------|---------|------------|
| `GET` | `/api/orders/` | List user-related orders |
| `POST` | `/api/orders/` | Create a new order (customers only) |
| `PATCH` | `/api/orders/{id}/` | Update an order |
| `DELETE` | `/api/orders/{id}/` | Delete an order (admin only) |

### 🛥️ **Reviews**
| Method | Endpoint | Description |
|--------|---------|------------|
| `GET` | `/api/reviews/` | List all reviews (filtered by user type) |
| `POST` | `/api/reviews/` | Create a review (customers only) |
| `PATCH` | `/api/reviews/{id}/` | Update a review (reviewer or admin only) |
| `DELETE` | `/api/reviews/{id}/` | Delete a review (reviewer or admin only) |

---

## 🔒 Permissions & Role-Based Access
- **Customers**: Can create orders and leave reviews.
- **Business Users**: Can create offers and manage orders.
- **Admins**: Can delete offers, orders, and reviews.
- **Authentication Required** for all actions.

---

## 🔥 Features to Be Added
- **Email verification** for new users.
- **Payment integration** for orders.
- **Improved filtering & searching** with Django Filters.

---

## 🤝 Contributing
1. Fork the repository.
2. Create a new branch (`feature-xyz`).
3. Commit your changes (`git commit -m "Added new feature"`).
4. Push to the branch (`git push origin feature-xyz`).
5. Open a **Pull Request**.

---

## 🐝 License
This project is for educational purposes and is licensed under **MIT License**.

---

## 📩 Contact
📧 **Your Name** - [mail@dogan-celik.com](mailto:mail@dogan-celik.com)  
🔗 **GitHub** - [github.com/Dogan36](https://github.com/Dogan36)  
🔗 **LinkedIn** - [linkedin.com](https://linkedin.com/in/doğan-çelik-29a412235)
```

