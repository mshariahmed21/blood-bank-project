
from flask import Flask, render_template, request

app = Flask(__name__)

# بيانات تجريبية فقط، وليست متبرعين حقيقيين

# بيانات تجريبية فقط، وليست متبرعين حقيقيين
DONORS = [

    {"name": "سعود محمد", "blood_type": "O+", "city": "الرياض"},
    {"name": "نواف علي", "blood_type": "A+", "city": "جدة"},
    {"name": "ريم أحمد", "blood_type": "B+", "city": "مكة المكرمة"},
    {"name": "فيصل خالد", "blood_type": "AB+", "city": "المدينة المنورة"},
    {"name": "لولوة حسن", "blood_type": "O-", "city": "الدمام"},
    {"name": "تركي سالم", "blood_type": "A-", "city": "الخبر"},
    {"name": "جود عبدالله", "blood_type": "B-", "city": "أبها"},
    {"name": "راكان فهد", "blood_type": "AB-", "city": "نجران"},
    {"name": "منى يحيى", "blood_type": "O+", "city": "تبوك"},
    {"name": "عبدالعزيز حسن", "blood_type": "A+", "city": "حائل"},
    {"name": "هند محمد", "blood_type": "B+", "city": "بريدة"},
    {"name": "ماجد علي", "blood_type": "AB+", "city": "عرعر"},
    {"name": "ليان خالد", "blood_type": "O-", "city": "سكاكا"},
    {"name": "بدر أحمد", "blood_type": "A-", "city": "الباحة"},
    {"name": "شهد سالم", "blood_type": "B-", "city": "صبيا"},
    {"name": "فهد يحيى", "blood_type": "AB-", "city": "جازان"},
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

