# Vetovo

The health record infrastructure behind **Animitr**.

Vetovo is an internal platform that provides every animal in the Animitr ecosystem with a persistent, lifelong digital health record. It is designed for veterinarians and administrators rather than pet owners, serving as the medical data layer of the broader Animal Identity Infrastructure.

**Production:** www.vetovo.in

---

## Overview

Animal medical records are often fragmented across clinics, paper files, or individual veterinarians, making long-term continuity of care difficult.

Vetovo addresses this by maintaining a single, persistent health record for every registered animal. Regardless of where an animal is treated, its medical history remains connected to the same identity.

Rather than functioning as a standalone veterinary practice management system, Vetovo serves as the medical record backbone of the Animitr ecosystem.

---

## Features

- Persistent digital health records
- Animal profile management
- Vaccination tracking
- Treatment history
- Visit records
- Role-based access for veterinarians and administrators
- Centralized medical history across clinics

---

## How It Works

Veterinarians and administrators authenticate through the platform and can:

- Search for registered animals
- View complete medical histories
- Record vaccinations
- Add treatment notes
- Log veterinary visits
- Manage veterinarian accounts and permissions

Every update becomes part of the animal's permanent medical record.

---

## Architecture

The frontend consists of static HTML, CSS, and JavaScript served directly by Nginx.

A Flask backend exposes the API running as a dedicated `systemd` service on the same EC2 instance as the Animitr infrastructure.

Medical data is stored in a dedicated PostgreSQL database, isolated from the rescue case database while remaining part of the same infrastructure.

```
                Browser
                   │
                   ▼
              Nginx (SSL)
                   │
        ┌──────────┴──────────┐
        │                     │
 Static Frontend        Flask API
 (/var/www/vetovo)     (Port 6000)
        │                     │
        └──────────┬──────────┘
                   │
                   ▼
              PostgreSQL
```

---

## Tech Stack

### Backend

- Python
- Flask
- PostgreSQL

### Frontend

- HTML
- CSS
- JavaScript

### Infrastructure

- AWS EC2
- Nginx
- systemd
- Let's Encrypt

---

## Project Structure

```
vetovo/

├── app.py
├── static/
├── templates/
├── models/
├── routes/
├── migrations/
├── requirements.txt
├── .env.example
└── README.md
```

> Adjust the structure above if your repository differs.

---

## Pages

| Page | Purpose |
|-------|---------|
| `index.html` | Login page |
| `admin.html` | Administration dashboard |
| `pets.html` | Animal profiles and medical history |
| `vets.html` | Veterinarian management |

---

## Data Model

The system revolves around a persistent **Animal Profile**.

Each profile maintains relationships with:

- Vaccination records
- Treatment records
- Visit history
- Assigned veterinarians

This design allows a complete medical history to be reconstructed using a single animal identifier.

Veterinarian accounts use role-based permissions, allowing administrators full access while limiting veterinarians to authorized records.

---

## Running Locally

Clone the repository:

```bash
git clone https://github.com/rangandhruv1234-collab/vetovo.git
cd vetovo
```

Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure environment variables:

```bash
cp .env.example .env
```

Start the application:

```bash
python app.py
```

The frontend is static and can be served through any local web server or opened directly in a browser.

---

## Environment Variables

```env
DATABASE_URL=
SECRET_KEY=
ADMIN_EMAIL=
```

Configure these values in `.env` before starting the application.

---

## Deployment

Production runs behind Nginx as a dedicated `systemd` service.

Restart the application:

```bash
sudo systemctl restart vetovo.service
```

Check status:

```bash
sudo systemctl status vetovo.service
```

View logs:

```bash
sudo journalctl -u vetovo.service -f
```

Static frontend files are served directly from `/var/www/vetovo/` and can be updated without restarting the backend service.

---

## Role Within Animitr

Vetovo is one component of the broader Animitr platform.

It provides the medical history layer that complements rescue coordination, animal identity, and future services such as ethical breeder verification and adoption.

While citizens primarily interact with Animitr, veterinarians interact with Vetovo to maintain accurate, lifelong medical records.

---

## Roadmap

Planned improvements include:

- Automatic profile creation from rescue cases
- Integration with the Animitr Rescue Bot
- Hospital management tools
- Medical analytics
- Appointment management
- Digital prescriptions
- API integrations for veterinary clinics

---

## About Animitr

Animitr is building the digital infrastructure for animal welfare in India.

The ecosystem includes AI-powered rescue coordination, persistent animal identity, lifelong health records, ethical breeder verification, adoption services, and community-funded care.

---

## Contact

Email: contact.animitr@gmail.com

Website: https://animitr.org
