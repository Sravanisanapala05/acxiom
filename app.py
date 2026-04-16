import pandas as pd
import gradio as gr
from datetime import datetime, timedelta

# ---------------- GLOBAL ----------------
user_fines = {}
issued_books = {}
current_user = None
current_role = None

# ---------------- DATA ----------------
users = pd.DataFrame({
    "user_id": ["adm","user"],
    "password": ["adm","user"],
    "role": ["admin","user"]
})

books = pd.DataFrame({
    "Serial No":[101,102,103],
    "Name":["A","B","C"],
    "Author":["Author A","Author B","Author C"],
    "Category":["Science","Economics","Fiction"],
    "Available":["Y","Y","N"]
})

product_details = pd.DataFrame({
    "Code No From":["SC(B/M)000001","EC(B/M)000001","FC(B/M)000001"],
    "Code No To":["SC(B/M)000000","EC(B/M)000000","FC(B/M)000000"],
    "Category":["Science","Economics","Fiction"]
})

# ---------------- FUNCTIONS ----------------

def validate_required(*fields):
    return all(f not in [None, ""] for f in fields)

def get_books():
    return [f"{n} ({c})" for n,c in zip(books["Name"],books["Category"])]

def login(uid, pwd):
    global current_user, current_role
    user = users[(users.user_id==uid)&(users.password==pwd)]
    if len(user)==0:
        return "Invalid Login", False

    current_user = uid
    current_role = user.iloc[0]["role"]

    return f"Logged in as {current_role}", True

def logout():
    return "You have successfully logged out.", False

def autofill_author(book):
    if not book:
        return ""
    name = book.split(" (")[0]
    rec = books[books["Name"]==name]
    return rec.iloc[0]["Author"] if not rec.empty else ""

def check_availability(book):
    if not book:
        return "Select a book", gr.update(interactive=False)

    name = book.split(" (")[0]
    rec = books[books["Name"]==name]

    if rec.iloc[0]["Available"]=="N":
        return "Book is not available", gr.update(interactive=False)

    return "Book is available", gr.update(interactive=True)

def issue_book(book):
    if not validate_required(book):
        return "Please select a book"

    name = book.split(" (")[0]
    idx = books[books["Name"]==name].index

    if books.loc[idx[0],"Available"]=="N":
        return "Book is not available"

    issue_date = datetime.today()
    return_date = issue_date + timedelta(days=15)

    books.loc[idx[0],"Available"]="N"

    issued_books[current_user] = {
        "book": name,
        "issue_date": issue_date,
        "return_date": return_date
    }

    return f"Issued successfully. Return by {return_date.date()}"

def return_book(book, serial, actual_return_date, fine_paid):
    if not validate_required(book, serial, actual_return_date):
        return "All mandatory fields required"

    if current_user not in issued_books:
        return "No book issued"

    data = issued_books[current_user]
    issue_date = data["issue_date"]
    expected_return = data["return_date"]

    actual = datetime.strptime(actual_return_date,"%Y-%m-%d")

    if actual < issue_date:
        return "Return date cannot be before issue date"

    if (actual - issue_date).days > 15:
        return "Return date cannot exceed 15 days"

    delay = (actual - expected_return).days

    if delay > 0:
        fine = delay * 5
        user_fines[current_user] = fine

        if not fine_paid:
            return f"Fine ₹{fine} pending. Pay fine first."

    books.loc[books["Name"]==data["book"],"Available"]="Y"
    issued_books.pop(current_user)

    return "Transaction completed successfully."

def check_fine():
    fine = user_fines.get(current_user,0)
    if fine == 0:
        return "No pending fines"
    return f"Pending fine amount: ₹{fine}"

def pay_fine(confirm):
    fine = user_fines.get(current_user,0)

    if fine == 0:
        return "No pending fines"

    if not confirm:
        return "Select fine paid checkbox"

    user_fines[current_user] = 0
    return "Fine paid successfully"

# ---------------- UI ----------------

with gr.Blocks(theme=gr.themes.Soft()) as app:

    state = gr.State(False)

    gr.Markdown("# ACXIOMI Library Management System")

    uid = gr.Textbox(label="User ID")
    pwd = gr.Textbox(label="Password", type="password")
    login_msg = gr.Textbox(label="Login Status")

    login_btn = gr.Button("Login")

    main = gr.Column(visible=False)

    with main:

        with gr.Tab("Home"):
            gr.Dataframe(product_details)

        with gr.Tab("Transactions"):
            book = gr.Radio(get_books(), label="Select Book")
            author = gr.Textbox(label="Author Name", interactive=False)

            book.change(autofill_author, book, author)

            status = gr.Textbox(label="Availability")
            issue_btn = gr.Button("Issue Book", interactive=False)

            book.change(check_availability, book, [status, issue_btn])

            issue_out = gr.Textbox(label="Issue Status")
            issue_btn.click(issue_book, book, issue_out)

            serial = gr.Textbox(label="Serial Number")
            return_date = gr.Textbox(label="Return Date (YYYY-MM-DD)")
            fine_paid = gr.Checkbox(label="Fine Paid")

            return_out = gr.Textbox(label="Return Status")

            gr.Button("Return Book").click(
                return_book,
                [book, serial, return_date, fine_paid],
                return_out
            )

            fine_status = gr.Textbox(label="Fine Status")
            fine_check = gr.Checkbox(label="Confirm Payment")

            gr.Button("Check Fine").click(check_fine, None, fine_status)
            gr.Button("Pay Fine").click(pay_fine, fine_check, fine_status)

        with gr.Tab("Maintenance"):
            gr.Markdown("Admin Section")

        with gr.Tab("Reports"):
            gr.Dataframe(books)

        logout_btn = gr.Button("Log Out")

    login_btn.click(login, [uid,pwd], [login_msg,state]).then(
        lambda x: gr.update(visible=x),
        state,
        main
    )

    logout_btn.click(logout, None, [login_msg,state]).then(
        lambda x: gr.update(visible=x),
        state,
        main
    )

app.launch(server_name="0.0.0.0", server_port=7860)