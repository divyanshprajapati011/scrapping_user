# 🚀 Maps Scraper (Streamlit + Supabase)

A Google Maps Scraper web application built with **Streamlit** and **Supabase (PostgreSQL)**.  
This tool allows users to search businesses on Google Maps using **SerpAPI**, extract details like name, address, phone, email, and export results in **CSV/Excel**.

---

## ✨ Features
- 🔑 User Authentication (Signup/Login with password hashing)
- 📱 Mobile Number, Email & Username registration
- 🗂️ Logs **Login History** & **Search History**
- 🔍 Scrapes Google Maps businesses using **SerpAPI**
- 📧 Optionally extracts **emails & phone numbers** from business websites
- 📥 Export results as **CSV** or **Excel**
- 📊 Admin Dashboard (via Supabase) for user and activity tracking

---

## 🛠️ Tech Stack
- [Streamlit](https://streamlit.io/) – Web UI
- [Supabase](https://supabase.com/) – PostgreSQL Database
- [psycopg2](https://www.psycopg.org/) – PostgreSQL Connector
- [SerpAPI](https://serpapi.com/) – Google Maps Scraping
- [Pandas](https://pandas.pydata.org/) – Data handling & export
- [OpenPyXL](https://openpyxl.readthedocs.io/) – Excel Export

---



##🗄️ Database Schema
users
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    mobile_number VARCHAR(20),
    password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

login_history
CREATE TABLE login_history (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(100)
);

search_history
CREATE TABLE search_history (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    query TEXT NOT NULL,
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

##🚀 Usage

Open app in browser → http://localhost:8501

Signup with username, email, mobile, password

Login and start scraping

View scraped results in interactive table

Download results as CSV/Excel

##📊 Admin Dashboard

Using Supabase dashboard, you can:

Manage users

View login history

View search history

Track scraping activity

##🔐 Security

Passwords are hashed with SHA256 before storing

Database connection is SSL secured

API Keys should be stored in .env file

##📜 License

This project is open-source. Use it for learning and personal projects.
For commercial use, check SerpAPI usage limits & pricing.

##👨‍💻 Developed by Deepak Prajapat
