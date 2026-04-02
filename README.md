<img width="100" height="100" alt="k2" src="https://github.com/user-attachments/assets/847a9d50-7843-4779-82fb-4d74eb7b2aed" />

# Kairva.LD 

A full-stack internship management platform built for **LD College of Engineering's Instrumentation & Control (IC) Branch** to streamline the entire internship allocation process — from posting opportunities to tracking applications and placements.

🔗 **Live Demo:** [kairvald.vercel.app](https://kairvald.vercel.app/)

## Features

- **Students** — Register, complete profile, browse & apply to internships, track application status, receive notifications
- **Companies** — Register, post internships, review applications, shortlist/hire candidates
- **Admin** — Verify companies & students, manage all jobs, edit profiles, platform oversight
- **Auth** — Google Sign-In and Email/Password via Firebase Authentication
- **Storage** — Resumes and profile pictures stored in Supabase Storage
- **Placement Records** — Historical internship placement data and analytics

## Screenshots
<img width="2850" height="1465" alt="image" src="https://github.com/user-attachments/assets/883c49be-8cc1-482f-8ba5-797c67a35f09" />
<img width="2861" height="1446" alt="image" src="https://github.com/user-attachments/assets/ff86c94e-ddae-4fa2-8a4d-9305e5a5c7ca" />


## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask (Python) |
| Auth | Firebase Admin SDK |
| Database | PostgreSQL via Supabase |
| Storage | Supabase Storage |
| Frontend | Jinja2 Templates, Vanilla JS, CSS |
| Icons | Lucide Icons |
| Deployment | Vercel / Render |

## Project Structure

```
├── main.py                  # Entry point
├── app/
│   ├── __init__.py          # Flask app factory, config, security headers
│   ├── routes.py            # All route handlers
│   ├── db.py                # Database layer (PostgreSQL)
│   ├── firebase_config.py   # Firebase Admin SDK setup
│   ├── supabase_storage.py  # Supabase file upload/signed URLs
│   ├── static/              # CSS, JS, images
│   └── templates/           # Jinja2 HTML templates
├── requirements.txt
├── vercel.json              # Vercel deployment config
└── .env.example             # Environment variable template
```


## Contributors

- **Kavin Jindal**
- **Sarthakk Anjariya**
