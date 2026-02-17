from flask import Flask, render_template, request, redirect, session, url_for
from config import Config
from models import OrderItem, db, bcrypt, User, Product, Cart, Order

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
bcrypt.init_app(app)

with app.app_context():
    db.create_all()

# ---------------- HOME ----------------
@app.route('/')
def home():
    return render_template("index.html")

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_pw = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        user = User(
            name=request.form['name'],
            email=request.form['email'],
            password=hashed_pw,
            role=request.form['role']
        )
        db.session.add(user)
        db.session.commit()

        return redirect('/login')

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()

        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect('/dashboard')

    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    return render_template("dashboard.html", role=session.get('role'))


# ---------------- ADD PRODUCT (Vendor) ----------------
@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if session.get('role') != "vendor":
        return "Unauthorized"

    if request.method == 'POST':
        product = Product(
            name=request.form['name'],
            price=request.form['price'],
            quantity=request.form['quantity'],
            vendor_id=session['user_id']
        )
        db.session.add(product)
        db.session.commit()
        return redirect('/products')

    return render_template("add_product.html")

# ---------------- VIEW PRODUCTS ----------------
@app.route('/products')
def products():
    all_products = Product.query.all()
    return render_template("products.html", products=all_products)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == "__main__":
    app.run(debug=True)
    
    
    
# ---------------- ADD TO CART ----------------
@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session:
        return redirect('/login')

    existing = Cart.query.filter_by(
        user_id=session['user_id'],
        product_id=product_id
    ).first()

    if existing:
        existing.quantity += 1
    else:
        cart = Cart(
            user_id=session['user_id'],
            product_id=product_id,
            quantity=1
        )
        db.session.add(cart)

    db.session.commit()
    return redirect('/cart')


# ---------------- VIEW CART ----------------
@app.route('/cart')
def view_cart():
    carts = Cart.query.filter_by(user_id=session['user_id']).all()

    cart_items = []
    total = 0

    for c in carts:
        product = Product.query.get(c.product_id)
        subtotal = product.price * c.quantity
        total += subtotal

        cart_items.append({
            "product": product,
            "quantity": c.quantity,
            "subtotal": subtotal
        })

    return render_template("cart.html", cart_items=cart_items, total=total)



@app.route('/checkout')
def checkout():
    carts = Cart.query.filter_by(user_id=session['user_id']).all()

    total = 0
    order = Order(user_id=session['user_id'], total_price=0)
    db.session.add(order)
    db.session.commit()

    for c in carts:
        product = Product.query.get(c.product_id)
        subtotal = product.price * c.quantity
        total += subtotal

        product.quantity -= c.quantity

        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=c.quantity
        )
        db.session.add(order_item)

    order.total_price = total
    Cart.query.filter_by(user_id=session['user_id']).delete()
    db.session.commit()

    return render_template("success.html", total=total)



@app.route('/admin/users')
def view_users():
    if session.get('role') != 'admin':
        return "Unauthorized"

    users = User.query.all()
    return render_template("admin_users.html", users=users)


@app.route('/admin/orders')
def view_orders():
    if session.get('role') != 'admin':
        return "Unauthorized"

    orders = Order.query.all()
    return render_template("admin_orders.html", orders=orders)


@app.route('/admin/update_order/<int:order_id>', methods=['POST'])
def update_order(order_id):
    if session.get('role') != 'admin':
        return "Unauthorized"

    order = Order.query.get(order_id)
    order.status = request.form['status']
    db.session.commit()

    return redirect('/admin/orders')
