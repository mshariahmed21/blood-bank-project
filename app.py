
from flask import Flask, render_template, request

app = Flask(__name__)

# بيانات تجريبية فقط، وليست متبرعين حقيقيين
DONORS = [
    {"name": "أحمد علي", "blood_type": "O-", "city": "جازان"},
    {"name": "خالد عمر", "blood_type": "A+", "city": "جازان"},
    {"name": "سارة محمد", "blood_type": "AB-", "city": "جازان"},
    {"name": "فهد عبدالله", "blood_type": "B+", "city": "صبيا"},
    {"name": "نورة أحمد", "blood_type": "O+", "city": "أبو عريش"},
    {"name": "محمد حسن", "blood_type": "B-", "city": "جازان"},
    {"name": "ريم علي", "blood_type": "A-", "city": "صبيا"},
    {"name": "عبدالله سالم", "blood_type": "AB+", "city": "أبو عريش"},
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

