
from flask import Flask, render_template, request

app = Flask(__name__)

# بيانات تجريبية فقط، وليست متبرعين حقيقيين

# بيانات تجريبية فقط، وليست متبرعين حقيقيين
DONORS = [
    {"name": "أحمد علي", "blood_type": "O-", "city": "جازان"},
    {"name": "خالد عمر", "blood_type": "O+", "city": "جازان"},
    {"name": "سارة محمد", "blood_type": "A-", "city": "صبيا"},
    {"name": "فهد عبدالله", "blood_type": "A+", "city": "جازان"},
    {"name": "نورة أحمد", "blood_type": "B-", "city": "أبو عريش"},
    {"name": "محمد حسن", "blood_type": "B+", "city": "صبيا"},
    {"name": "ريم علي", "blood_type": "AB-", "city": "جازان"},
    {"name": "عبدالله سالم", "blood_type": "AB+", "city": "أبو عريش"},
    {"name": "سلمان يحيى", "blood_type": "O-", "city": "صبيا"},
    {"name": "منى حسن", "blood_type": "O+", "city": "أبو عريش"},
    {"name": "تركي أحمد", "blood_type": "A-", "city": "جازان"},
    {"name": "جود محمد", "blood_type": "A+", "city": "صبيا"},
    {"name": "فيصل علي", "blood_type": "B-", "city": "جازان"},
    {"name": "لمى خالد", "blood_type": "B+", "city": "أبو عريش"},
    {"name": "راكان سالم", "blood_type": "AB-", "city": "صبيا"},
    {"name": "هيا عبدالله", "blood_type": "AB+", "city": "جازان"},
]


@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    selected_type = ""
    selected_city = ""
    searched = False

    if request.method == "POST":
        searched = True
        selected_type = request.form.get("blood_type", "")
        selected_city = request.form.get("city", "")

        results = [
            donor for donor in DONORS
            if (not selected_type or donor["blood_type"] == selected_type)
            and (not selected_city or donor["city"] == selected_city)
        ]

    return render_template(
        "index.html",
        results=results,
        selected_type=selected_type,
        selected_city=selected_city,
        searched=searched,
    )


if __name__ == "__main__":
    app.run(debug=True)

