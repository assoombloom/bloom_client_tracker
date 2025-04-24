import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import urllib.parse

st.set_page_config(page_title="سجل عملاء bloom for microblading", layout="wide")
st.image("bloom_logo_resized.png", width=150)
st.title("سجل عملاء bloom for microblading")

DATA_FILE = "clients_data.csv"

def load_data():
    if Path(DATA_FILE).exists():
        return pd.read_csv(DATA_FILE, parse_dates=["تاريخ الجلسة", "موعد الريتتش"])
    else:
        return pd.DataFrame(columns=["اسم العميل", "رقم الهاتف", "نوع الخدمة", "تاريخ الجلسة",
                                     "موعد الريتتش", "المبلغ المدفوع", "ملاحظات", "تم التذكير", "انتهت الجلسات"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def calculate_retouch(service, session_date):
    if service == "توريد":
        return session_date + timedelta(days=45)
    else:
        return session_date + timedelta(days=30)

def get_status(row):
    today = datetime.today().date()
    if row["انتهت الجلسات"] == "نعم":
        return "☑️ انتهت الجلسات", "red"
    elif row["تم التذكير"] == "نعم":
        return "☑️ تم التذكير", "green"
    elif row["موعد الريتتش"].date() < today:
        return "🔴 متأخر", "orange"
    elif (row["موعد الريتتش"].date() - today).days <= 3:
        return "🟡 اقترب الموعد", "yellow"
    else:
        return "🟢 نشط", "blue"

if "edit_data" not in st.session_state:
    st.session_state.edit_data = None

df = load_data()

# ===== إضافة أو تعديل =====
with st.form("client_form"):
    st.subheader("➕ إضافة / تعديل عميل")

    if st.session_state.edit_data is not None:
        data = st.session_state.edit_data
        name = st.text_input("اسم العميل", value=data["اسم العميل"])
        phone = st.text_input("رقم الهاتف", value=data["رقم الهاتف"])
        service_type = st.selectbox("نوع الخدمة", ["مايكروبليدنج", "توريد", "ليزر", "الرموش"], index=["مايكروبليدنج", "توريد", "ليزر", "الرموش"].index(data["نوع الخدمة"]))
        session_date = st.date_input("تاريخ الجلسة", value=data["تاريخ الجلسة"].date())
        manual_retouch = st.date_input("موعد الريتتش", value=data["موعد الريتتش"].date())
        amount = st.number_input("المبلغ المدفوع", min_value=0.0, step=10.0, value=float(data["المبلغ المدفوع"]))
        notes = st.text_area("ملاحظات", value=data["ملاحظات"])
        edit_mode = True
    else:
        name = st.text_input("اسم العميل")
        phone = st.text_input("رقم الهاتف")
        service_type = st.selectbox("نوع الخدمة", ["مايكروبليدنج", "توريد", "ليزر", "الرموش"])
        session_date = st.date_input("تاريخ الجلسة", datetime.today())
        auto_retouch = calculate_retouch(service_type, session_date)
        manual_retouch = st.date_input("موعد الريتتش", value=auto_retouch)
        amount = st.number_input("المبلغ المدفوع", min_value=0.0, step=10.0)
        notes = st.text_area("ملاحظات")
        edit_mode = False

    submitted = st.form_submit_button("💾 حفظ")

    if submitted:
        new_entry = {
            "اسم العميل": name,
            "رقم الهاتف": phone,
            "نوع الخدمة": service_type,
            "تاريخ الجلسة": pd.to_datetime(session_date),
            "موعد الريتتش": pd.to_datetime(manual_retouch),
            "المبلغ المدفوع": amount,
            "ملاحظات": notes,
            "تم التذكير": "لا",
            "انتهت الجلسات": "لا"
        }

        if edit_mode and st.session_state.edit_data is not None:
            idx = df[(df["اسم العميل"] == st.session_state.edit_data["اسم العميل"]) & 
                     (df["رقم الهاتف"] == st.session_state.edit_data["رقم الهاتف"])].index
            if not idx.empty:
                df.loc[idx[0]] = new_entry
                st.success("تم تعديل بيانات العميل.")
            st.session_state.edit_data = None
        else:
            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
            st.success("تمت إضافة العميل.")

        save_data(df)
        st.rerun()

# ===== بحث وفلترة =====
st.subheader("🔎 البحث")
colA, colB, colC = st.columns(3)
search_name = colA.text_input("بحث بالاسم")
search_service = colB.selectbox("بحث بالخدمة", ["", "مايكروبليدنج", "توريد", "ليزر", "رموش"])
search_date = colC.date_input("بحث بالتاريخ", value=None)

filtered_df = df.copy()
if search_name:
    filtered_df = filtered_df[filtered_df["اسم العميل"].str.contains(search_name, case=False, na=False)]
if search_service:
    filtered_df = filtered_df[filtered_df["نوع الخدمة"] == search_service]
if search_date:
    filtered_df = filtered_df[filtered_df["تاريخ الجلسة"] == pd.to_datetime(search_date)]

st.markdown("---")
st.subheader("📋 قائمة العملاء")

if st.checkbox("👀 عرض فقط العملاء القريبين (3 أيام القادمة)"):
    today = datetime.today().date()
    filtered_df = filtered_df[(filtered_df["موعد الريتتش"].dt.date - today).between(0, 3)]

if not filtered_df.empty:
    filtered_df = filtered_df.sort_values("تاريخ الجلسة")
    for i, row in filtered_df.iterrows():
        الحالة, اللون = get_status(row)
        with st.expander(f"{row['اسم العميل']} - {row['نوع الخدمة']} | {row['تاريخ الجلسة'].date()}"):
            st.markdown(f"**الحالة:** :{اللون}[{الحالة}]")
            st.write(f"**موعد الريتتش:** {row['موعد الريتتش'].date()}")
            st.write(f"**المبلغ المدفوع:** {row['المبلغ المدفوع']} جنيه")
            st.write(f"**ملاحظات:** {row['ملاحظات']}")

            col1, col2, col3, col4, col5 = st.columns(5)

            if row["تم التذكير"] != "نعم":
                if col1.button("☑️ تم التذكير", key=f"remind_{i}"):
                    df.at[i, "تم التذكير"] = "نعم"
                    save_data(df)
                    st.rerun()
            else:
                col1.success("☑️ تم التذكير")

            if row["انتهت الجلسات"] != "نعم":
                if col2.button("☑️ انتهت الجلسات", key=f"finish_{i}"):
                    df.at[i, "انتهت الجلسات"] = "نعم"
                    save_data(df)
                    st.rerun()
            else:
                col2.error("☑️ انتهت الجلسات")

            if col3.button("🗑️ حذف", key=f"delete_{i}"):
                df.drop(index=i, inplace=True)
                df.reset_index(drop=True, inplace=True)
                save_data(df)
                st.rerun()

            if col4.button("✏️ تعديل", key=f"edit_{i}"):
                st.session_state.edit_data = row
                st.rerun()

            msg = f"مرحباً {row['اسم العميل']}، تذكير بموعد جلستك الخاصة بـ {row['نوع الخدمة']} بتاريخ {row['موعد الريتتش'].date()}، شكراً لتعاملك معنا."
            link = f"https://wa.me/{row['رقم الهاتف']}?text={urllib.parse.quote(msg)}"
            col5.markdown(f"[📲 واتساب]({link})", unsafe_allow_html=True)

else:
    st.info("لا توجد نتائج مطابقة.")



# ===== تصدير البيانات إلى Excel =====
st.subheader("⬇️ تصدير البيانات")
import io
from openpyxl import Workbook

if st.button("📤 تحميل كملف Excel (xlsx)"):
    df_export = df.copy()
    df_export["تاريخ الجلسة"] = df_export["تاريخ الجلسة"].dt.date
    df_export["موعد الريتتش"] = df_export["موعد الريتتش"].dt.date

    towrite = io.BytesIO()
    df_export.to_excel(towrite, index=False, engine="openpyxl")
    towrite.seek(0)
    st.download_button("اضغط هنا لتنزيل الملف", towrite, file_name="clients_export.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
