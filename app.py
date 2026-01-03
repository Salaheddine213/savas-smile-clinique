# savas_smile_final.py
from flask import Flask, render_template_string, request, redirect, url_for, flash, session
from flask import send_from_directory, jsonify
import webbrowser
import threading
import os
import sqlite3
from datetime import datetime
import hashlib
import secrets
import functools

# ==================== CONFIGURATION ====================
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Configuration
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ADMIN_PATH'] = 'admin-secret-1234abcd'  # URL fixe pour le portfolio
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Créer les dossiers
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Base de données
DATABASE = 'savas_smile_final.db'

# ==================== FONCTIONS UTILITAIRES ====================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password_hash, password):
    return password_hash == hash_password(password)

def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return jsonify({'error': 'Non autorisé'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ==================== INITIALISATION DB ====================
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Table administrateurs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT
    )
    ''')
    
    # Table galerie
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS gallery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        before_image TEXT,
        after_image TEXT,
        category TEXT DEFAULT 'Invisalign',
        treatment_duration TEXT,
        visible INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Table rendez-vous
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        appointment_date DATE NOT NULL,
        appointment_time TEXT NOT NULL,
        treatment_type TEXT NOT NULL,
        message TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Admin par défaut
    cursor.execute("SELECT COUNT(*) FROM admin_users")
    if cursor.fetchone()[0] == 0:
        default_password = hash_password("Admin@2024")
        cursor.execute(
            "INSERT INTO admin_users (username, password_hash, email) VALUES (?, ?, ?)",
            ('admin', default_password, 'admin@savassmile.com')
        )
    
    # Données exemple
    cursor.execute("SELECT COUNT(*) FROM gallery")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO gallery (title, description, before_image, after_image, category, treatment_duration)
            VALUES 
            ('Sourire parfait en 6 mois', 'Traitement Invisalign complet', 
             'https://images.unsplash.com/photo-1588776814546-1ffcf47267a5?w=600',
             'https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=600',
             'Invisalign', '6 mois'),
            ('Blanchiment professionnel', 'Résultats immédiats et durables',
             'https://images.unsplash.com/photo-1544006659-f0b21884ce1d?w=600',
             'https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=600',
             'Blanchiment', '1 séance'),
            ('Alignement rapide', 'Correction en seulement 4 mois',
             'https://images.unsplash.com/photo-1560250097-0b93528c311a?w=600',
             'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=600',
             'Invisalign', '4 mois')
        ''')
    
    # Rendez-vous exemple
    cursor.execute("SELECT COUNT(*) FROM appointments")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO appointments (full_name, email, phone, treatment_type, message, appointment_date, appointment_time, status)
            VALUES 
            ('Sophie Martin', 'sophie@email.com', '0612345678', 'invisalign', 'Première consultation', '2024-01-15', '14:30', 'confirmed'),
            ('Thomas Bernard', 'thomas@email.com', '0623456789', 'blanchiment', 'Intéressé par le blanchiment', '2024-01-16', '10:00', 'pending'),
            ('Marie Dubois', 'marie@email.com', '0634567890', 'consultation', 'Renseignements généraux', '2024-01-17', '16:45', 'confirmed')
        ''')
    
    conn.commit()
    conn.close()

# Initialiser
init_db()

# ==================== TEMPLATE SITE PUBLIC ====================
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Savaş Smile | Orthodontie Invisible Expert</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Playfair+Display:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        :root {
            --primary: #00b4d8;
            --primary-dark: #0096c7;
            --secondary: #ff6b6b;
            --accent: #ffd166;
            --light: #f8f9fa;
            --dark: #212529;
            --gray: #6c757d;
            --transition: all 0.3s ease;
        }
        
        body {
            font-family: 'Poppins', sans-serif;
            color: var(--dark);
            line-height: 1.6;
            overflow-x: hidden;
        }
        
        /* Header et Navigation */
        .header {
            position: fixed;
            top: 0;
            width: 100%;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            z-index: 1000;
            box-shadow: 0 2px 20px rgba(0, 0, 0, 0.1);
            transition: var(--transition);
        }
        
        .nav-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            font-family: 'Playfair Display', serif;
            font-size: 2rem;
            font-weight: 600;
            color: var(--primary);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .logo i {
            color: var(--accent);
        }
        
        .nav-links {
            display: flex;
            gap: 2rem;
            list-style: none;
        }
        
        .nav-links a {
            text-decoration: none;
            color: var(--dark);
            font-weight: 500;
            transition: var(--transition);
            position: relative;
        }
        
        .nav-links a:hover {
            color: var(--primary);
        }
        
        .nav-links a::after {
            content: '';
            position: absolute;
            bottom: -5px;
            left: 0;
            width: 0;
            height: 2px;
            background: var(--primary);
            transition: var(--transition);
        }
        
        .nav-links a:hover::after {
            width: 100%;
        }
        
        .cta-button {
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white;
            padding: 0.8rem 2rem;
            border-radius: 50px;
            text-decoration: none;
            font-weight: 600;
            transition: var(--transition);
            box-shadow: 0 4px 15px rgba(0, 180, 216, 0.3);
        }
        
        .cta-button:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(0, 180, 216, 0.4);
        }
        
        /* Hero Section */
        .hero {
            min-height: 100vh;
            background: linear-gradient(rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.9)),
                        url('https://images.unsplash.com/photo-1588776814546-1ffcf47267a5?auto=format&fit=crop&w=1350');
            background-size: cover;
            background-position: center;
            display: flex;
            align-items: center;
            padding: 6rem 2rem 2rem;
        }
        
        .hero-content {
            max-width: 1200px;
            margin: 0 auto;
            text-align: center;
        }
        
        .hero h1 {
            font-family: 'Playfair Display', serif;
            font-size: 3.5rem;
            margin-bottom: 1.5rem;
            color: var(--dark);
            line-height: 1.2;
        }
        
        .hero p {
            font-size: 1.2rem;
            color: var(--gray);
            max-width: 600px;
            margin: 0 auto 2rem;
        }
        
        .price-tag {
            display: inline-block;
            background: var(--accent);
            color: var(--dark);
            padding: 1rem 2rem;
            border-radius: 10px;
            font-size: 2rem;
            font-weight: 700;
            margin: 2rem 0;
            box-shadow: 0 4px 15px rgba(255, 209, 102, 0.3);
        }
        
        /* Features Grid */
        .features {
            padding: 5rem 2rem;
            background: var(--light);
        }
        
        .section-title {
            text-align: center;
            font-family: 'Playfair Display', serif;
            font-size: 2.5rem;
            margin-bottom: 3rem;
            color: var(--dark);
        }
        
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .feature-card {
            background: white;
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            transition: var(--transition);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }
        
        .feature-card:hover {
            transform: translateY(-10px);
            box-shadow: 0 15px 30px rgba(0, 0, 0, 0.15);
        }
        
        .feature-icon {
            font-size: 3rem;
            color: var(--primary);
            margin-bottom: 1rem;
        }
        
        /* Gallery */
        .gallery {
            padding: 5rem 2rem;
        }
        
        .gallery-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .gallery-item {
            position: relative;
            overflow: hidden;
            border-radius: 15px;
            height: 300px;
        }
        
        .gallery-item img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.5s ease;
        }
        
        .gallery-item:hover img {
            transform: scale(1.1);
        }
        
        /* Contact Form */
        .contact {
            padding: 5rem 2rem;
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white;
        }
        
        .contact-form {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            padding: 3rem;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        }
        
        .form-group {
            margin-bottom: 1.5rem;
        }
        
        .form-group input,
        .form-group textarea,
        .form-group select {
            width: 100%;
            padding: 1rem;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            font-family: 'Poppins', sans-serif;
            transition: var(--transition);
        }
        
        .form-group input:focus,
        .form-group textarea:focus,
        .form-group select:focus {
            outline: none;
            border-color: var(--primary);
        }
        
        /* Footer */
        .footer {
            background: var(--dark);
            color: white;
            padding: 4rem 2rem 2rem;
        }
        
        .footer-content {
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 3rem;
        }
        
        .social-links {
            display: flex;
            gap: 1rem;
            margin-top: 1rem;
        }
        
        .social-links a {
            color: white;
            font-size: 1.5rem;
            transition: var(--transition);
        }
        
        .social-links a:hover {
            color: var(--primary);
        }
        
        /* Animations */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .fade-in {
            animation: fadeIn 1s ease forwards;
        }
        
        .delay-1 { animation-delay: 0.2s; }
        .delay-2 { animation-delay: 0.4s; }
        .delay-3 { animation-delay: 0.6s; }
        
        /* Responsive */
        @media (max-width: 768px) {
            .nav-links {
                display: none;
            }
            
            .hero h1 {
                font-size: 2.5rem;
            }
            
            .mobile-menu-btn {
                display: block;
            }
        }
    </style>
</head>
<body>
    <!-- Header -->
    <header class="header">
        <nav class="nav-container">
            <div class="logo">
                <i class="fas fa-smile"></i>
                Savaş Smile <span style="color: var(--accent);">Premium</span>
            </div>
            <ul class="nav-links">
                <li><a href="#home">Accueil</a></li>
                <li><a href="#invisalign">Invisalign</a></li>
                <li><a href="#team">Notre Équipe</a></li>
                <li><a href="#treatments">Traitements</a></li>
                <li><a href="#contact">Contact</a></li>
            </ul>
            <a href="#contact" class="cta-button">
                <i class="fas fa-calendar-check"></i> Prendre RDV
            </a>
        </nav>
    </header>

    <!-- Hero Section -->
    <section class="hero" id="home">
        <div class="hero-content">
            <h1 class="fade-in">Redécouvrez le Plaisir de Sourire</h1>
            <p class="fade-in delay-1">Une orthodontie invisible, des résultats exceptionnels. Votre sourire redessiné par nos experts.</p>
            <div class="price-tag fade-in delay-2">
                Traitement Invisalign à partir de 13 000 DA
            </div>
            <div class="fade-in delay-3">
                <a href="#contact" class="cta-button" style="margin-right: 1rem;">
                    <i class="fas fa-comment-medical"></i> Consultation Gratuite
                </a>
                <a href="#team" class="cta-button" style="background: var(--secondary);">
                    <i class="fas fa-user-md"></i> Rencontrer l'Équipe
                </a>
            </div>
        </div>
    </section>

    <!-- Features -->
    <section class="features" id="invisalign">
        <h2 class="section-title">Pourquoi Choisir Savaş Smile ?</h2>
        <div class="features-grid">
            <div class="feature-card fade-in">
                <div class="feature-icon">
                    <i class="fas fa-user-md"></i>
                </div>
                <h3>Experts Certifiés</h3>
                <p>Nos orthodontistes sont spécialement formés aux techniques invisibles les plus avancées.</p>
            </div>
            <div class="feature-card fade-in delay-1">
                <div class="feature-icon">
                    <i class="fas fa-clock"></i>
                </div>
                <h3>Résultats Rapides</h3>
                <p>En moyenne 7 mois de traitement pour un sourire parfaitement aligné.</p>
            </div>
            <div class="feature-card fade-in delay-2">
                <div class="feature-icon">
                    <i class="fas fa-euro-sign"></i>
                </div>
                <h3>Transparence Tarifaire</h3>
                <p>Devis détaillé dès la première consultation, remboursée à 100%.</p>
            </div>
            <div class="feature-card fade-in delay-3">
                <div class="feature-icon">
                    <i class="fas fa-shield-alt"></i>
                </div>
                <h3>Garantie Satisfait</h3>
                <p>Plus de 3000 patients satisfaits depuis 15 ans d'expertise.</p>
            </div>
        </div>
    </section>

    <!-- Gallery -->
    <section class="gallery" id="team">
        <h2 class="section-title">Notre Équipe d'Experts</h2>
        <div class="gallery-grid">
            <div class="gallery-item">
                <img src="https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&w=600" alt="Orthodontiste">
                <div style="position: absolute; bottom: 0; background: rgba(0, 180, 216, 0.9); color: white; padding: 1rem; width: 100%;">
                    <h3>Dr. Ahmed Savaş</h3>
                    <p>Orthodontiste spécialisé Invisalign</p>
                </div>
            </div>
            <div class="gallery-item">
                <img src="https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?auto=format&fit=crop&w=600" alt="Centre Dentaire">
                <div style="position: absolute; bottom: 0; background: rgba(0, 180, 216, 0.9); color: white; padding: 1rem; width: 100%;">
                    <h3>Notre Centre</h3>
                    <p>Environnement moderne et accueillant</p>
                </div>
            </div>
            <div class="gallery-item">
                <img src="https://images.unsplash.com/photo-1588776814546-1ffcf47267a5?auto=format&fit=crop&w=600" alt="Technologie">
                <div style="position: absolute; bottom: 0; background: rgba(0, 180, 216, 0.9); color: white; padding: 1rem; width: 100%;">
                    <h3>Technologie de Pointe</h3>
                    <p>Scanner 3D et planification numérique</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Treatments -->
    <section class="features" id="treatments" style="background: white;">
        <h2 class="section-title">Nos Traitements Spécialisés</h2>
        <div class="features-grid">
            <div class="feature-card" style="border-top: 5px solid var(--primary);">
                <h3><i class="fas fa-teeth" style="color: var(--primary); margin-right: 10px;"></i> Invisalign</h3>
                <p>Aligneurs transparents et amovibles pour un traitement discret.</p>
                <div style="margin-top: 1rem; color: var(--primary); font-weight: 600; font-size: 1.3rem;">
                    À partir de 13 000 DA
                </div>
            </div>
            <div class="feature-card" style="border-top: 5px solid var(--secondary);">
                <h3><i class="fas fa-tooth" style="color: var(--secondary); margin-right: 10px;"></i> Blanchiment</h3>
                <p>Blanchiment dentaire professionnel avec résultats garantis.</p>
                <div style="margin-top: 1rem; color: var(--secondary); font-weight: 600; font-size: 1.3rem;">
                    À partir de 5 000 DA
                </div>
            </div>
            <div class="feature-card" style="border-top: 5px solid var(--accent);">
                <h3><i class="fas fa-teeth-open" style="color: var(--accent); margin-right: 10px;"></i> Implants</h3>
                <p>Réhabilitation complète avec implants dentaires de qualité.</p>
                <div style="margin-top: 1rem; color: var(--accent); font-weight: 600; font-size: 1.3rem;">
                    Sur devis personnalisé
                </div>
            </div>
        </div>
    </section>

    <!-- Contact -->
    <section class="contact" id="contact">
        <h2 class="section-title" style="color: white;">Prenez Rendez-vous</h2>
        <div class="contact-form">
            <h3 style="color: var(--dark); margin-bottom: 2rem;">Votre Première Consultation Offerte</h3>
            <form id="contactForm" method="POST" action="/prendre-rdv">
                <div class="form-group">
                    <input type="text" name="full_name" placeholder="Votre nom complet" required>
                </div>
                <div class="form-group">
                    <input type="email" name="email" placeholder="Votre email" required>
                </div>
                <div class="form-group">
                    <input type="tel" name="phone" placeholder="Votre téléphone" required>
                </div>
                <div class="form-group">
                    <select name="treatment_type" required>
                        <option value="">Choisissez un traitement</option>
                        <option value="invisalign">Invisalign - Orthodontie invisible</option>
                        <option value="blanchiment">Blanchiment dentaire</option>
                        <option value="implant">Implant dentaire</option>
                        <option value="consultation">Première consultation</option>
                    </select>
                </div>
                <div class="form-group">
                    <textarea name="message" placeholder="Votre message" rows="4"></textarea>
                </div>
                <button type="submit" class="cta-button" style="width: 100%; font-size: 1.1rem;">
                    <i class="fas fa-paper-plane"></i> Envoyer ma demande
                </button>
            </form>
        </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
        <div class="footer-content">
            <div>
                <div class="logo" style="font-size: 1.8rem; margin-bottom: 1rem;">
                    <i class="fas fa-smile"></i> Savaş Smile
                </div>
                <p>Votre spécialiste en orthodontie invisible depuis 15 ans.</p>
                <div class="social-links">
                    <a href="#"><i class="fab fa-facebook"></i></a>
                    <a href="#"><i class="fab fa-instagram"></i></a>
                    <a href="#"><i class="fab fa-linkedin"></i></a>
                    <a href="#"><i class="fab fa-google"></i></a>
                </div>
            </div>
            <div>
                <h3>Nos Centres</h3>
                <p><i class="fas fa-map-marker-alt"></i> Centre 1 - 17 rue Ferari El Habib (Larmoud)</p>
                <p><i class="fas fa-map-marker-alt"></i> Centre 2 - Terrain Boumedien N°15</p>
                <p><i class="fas fa-phone"></i> 05 XX XX XX XX</p>
            </div>
            <div>
                <h3>Horaires</h3>
                <p>Lundi - Vendredi: 9h-19h</p>
                <p>Samedi: 9h-18h</p>
                <p>Urgences: 7j/7 - 24h/24</p>
            </div>
        </div>
        <div style="text-align: center; margin-top: 3rem; padding-top: 2rem; border-top: 1px solid rgba(255,255,255,0.1);">
            <p>© 2024 Savaş Smile Premium. Tous droits réservés.</p>
        </div>
    </footer>

    <script>
        // Animation au scroll
        document.addEventListener('DOMContentLoaded', function() {
            const fadeElements = document.querySelectorAll('.fade-in');
            
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                    }
                });
            }, { threshold: 0.1 });
            
            fadeElements.forEach(el => {
                el.style.opacity = '0';
                el.style.transform = 'translateY(20px)';
                el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
                observer.observe(el);
            });
            
            // Form submission
            document.getElementById('contactForm').addEventListener('submit', function(e) {
                e.preventDefault();
                fetch(this.action, {
                    method: 'POST',
                    body: new FormData(this)
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('Merci ! Votre demande a été envoyée. Nous vous contacterons dans les 24h.');
                        this.reset();
                    } else {
                        alert('Erreur: ' + data.error);
                    }
                })
                .catch(error => {
                    alert('Erreur de connexion. Veuillez réessayer.');
                });
            });
            
            // Smooth scroll
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                anchor.addEventListener('click', function(e) {
                    e.preventDefault();
                    const targetId = this.getAttribute('href');
                    if(targetId === '#') return;
                    
                    const targetElement = document.querySelector(targetId);
                    if(targetElement) {
                        window.scrollTo({
                            top: targetElement.offsetTop - 80,
                            behavior: 'smooth'
                        });
                    }
                });
            });
            
            // Header scroll effect
            window.addEventListener('scroll', function() {
                const header = document.querySelector('.header');
                if (window.scrollY > 100) {
                    header.style.background = 'rgba(255, 255, 255, 0.98)';
                    header.style.boxShadow = '0 5px 20px rgba(0, 0, 0, 0.1)';
                } else {
                    header.style.background = 'rgba(255, 255, 255, 0.95)';
                    header.style.boxShadow = '0 2px 20px rgba(0, 0, 0, 0.1)';
                }
            });
        });
    </script>
</body>
</html>
'''

# ==================== ROUTES PUBLIQUES ====================

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/prendre-rdv', methods=['POST'])
def take_appointment():
    try:
        data = request.form
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO appointments (full_name, email, phone, treatment_type, message, appointment_date, appointment_time)
            VALUES (?, ?, ?, ?, ?, date('now'), time('now'))
        ''', (
            data.get('full_name'),
            data.get('email'),
            data.get('phone'),
            data.get('treatment_type'),
            data.get('message', '')
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Rendez-vous enregistré avec succès'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== ROUTES ADMIN (API) ====================

@app.route(f'/{app.config["ADMIN_PATH"]}/login', methods=['POST'])
def admin_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin_users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user and verify_password(user[2], password):
        session['admin_logged_in'] = True
        session['username'] = username
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Identifiants incorrects'})

@app.route(f'/{app.config["ADMIN_PATH"]}/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return jsonify({'success': True})

@app.route(f'/{app.config["ADMIN_PATH"]}/dashboard')
@admin_required
def admin_dashboard():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Statistiques
    cursor.execute("SELECT COUNT(*) FROM appointments")
    total_appointments = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM appointments WHERE date(created_at) = date('now')")
    today_appointments = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'pending'")
    pending_appointments = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM gallery")
    total_cases = cursor.fetchone()[0]
    
    # Rendez-vous récents
    cursor.execute("SELECT * FROM appointments ORDER BY created_at DESC LIMIT 10")
    appointments = cursor.fetchall()
    
    appointments_list = []
    for row in appointments:
        appointments_list.append({
            'id': row[0],
            'full_name': row[1],
            'email': row[2],
            'phone': row[3],
            'appointment_date': row[6],
            'appointment_time': row[7],
            'treatment_type': row[4],
            'message': row[5],
            'status': row[8],
            'created_at': row[9]
        })
    
    # Galerie
    cursor.execute("SELECT * FROM gallery ORDER BY created_at DESC LIMIT 6")
    gallery = cursor.fetchall()
    
    gallery_list = []
    for row in gallery:
        gallery_list.append({
            'id': row[0],
            'title': row[1],
            'description': row[2],
            'before_image': row[3],
            'after_image': row[4],
            'category': row[5],
            'treatment_duration': row[6],
            'visible': row[7],
            'created_at': row[8]
        })
    
    # Données pour graphiques
    cursor.execute('''
        SELECT 
            strftime('%Y-%m', created_at) as month,
            COUNT(*) as count
        FROM appointments 
        WHERE created_at >= date('now', '-6 months')
        GROUP BY strftime('%Y-%m', created_at)
        ORDER BY month
    ''')
    appointments_by_month = cursor.fetchall()
    
    conn.close()
    
    return jsonify({
        'stats': {
            'total_appointments': total_appointments,
            'today_appointments': today_appointments,
            'pending_appointments': pending_appointments,
            'total_cases': total_cases
        },
        'appointments': appointments_list,
        'gallery': gallery_list,
        'charts': {
            'appointments_by_month': [
                {'month': row[0], 'count': row[1]} for row in appointments_by_month
            ]
        }
    })

@app.route(f'/{app.config["ADMIN_PATH"]}/appointments')
@admin_required
def get_appointments():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM appointments ORDER BY created_at DESC")
    appointments = cursor.fetchall()
    conn.close()
    
    appointments_list = []
    for row in appointments:
        appointments_list.append({
            'id': row[0],
            'full_name': row[1],
            'email': row[2],
            'phone': row[3],
            'treatment_type': row[4],
            'message': row[5],
            'appointment_date': row[6],
            'appointment_time': row[7],
            'status': row[8],
            'created_at': row[9]
        })
    
    return jsonify(appointments_list)

@app.route(f'/{app.config["ADMIN_PATH"]}/appointment/<int:app_id>/confirm', methods=['POST'])
@admin_required
def confirm_appointment(app_id):
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("UPDATE appointments SET status = 'confirmed' WHERE id = ?", (app_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route(f'/{app.config["ADMIN_PATH"]}/appointment/<int:app_id>/cancel', methods=['POST'])
@admin_required
def cancel_appointment(app_id):
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("UPDATE appointments SET status = 'cancelled' WHERE id = ?", (app_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route(f'/{app.config["ADMIN_PATH"]}/gallery', methods=['GET', 'POST'])
@admin_required
def manage_gallery():
    if request.method == 'GET':
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM gallery ORDER BY created_at DESC")
        gallery = cursor.fetchall()
        conn.close()
        
        gallery_list = []
        for row in gallery:
            gallery_list.append({
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'before_image': row[3],
                'after_image': row[4],
                'category': row[5],
                'treatment_duration': row[6],
                'visible': row[7],
                'created_at': row[8]
            })
        
        return jsonify(gallery_list)
    
    elif request.method == 'POST':
        try:
            data = request.json
            
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO gallery (title, description, before_image, after_image, category, treatment_duration)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data.get('title'),
                data.get('description', ''),
                data.get('before_image', ''),
                data.get('after_image', ''),
                data.get('category', 'Invisalign'),
                data.get('treatment_duration', '')
            ))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True})
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

@app.route(f'/{app.config["ADMIN_PATH"]}/gallery/<int:item_id>', methods=['DELETE'])
@admin_required
def delete_gallery_item(item_id):
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM gallery WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== PAGE ADMIN PROFESSIONNELLE ====================

ADMIN_PAGE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Admin | Savaş Smile</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        :root {
            --primary: #00b4d8;
            --primary-dark: #0096c7;
            --secondary: #ff6b6b;
            --accent: #ffd166;
            --dark-bg: #0f172a;
            --dark-card: #1e293b;
            --dark-border: #334155;
            --light-text: #f1f5f9;
            --gray-text: #94a3b8;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --transition: all 0.3s ease;
        }
        
        body {
            font-family: 'Poppins', sans-serif;
            background: var(--dark-bg);
            color: var(--light-text);
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        .admin-container {
            display: flex;
            min-height: 100vh;
        }
        
        /* Sidebar */
        .sidebar {
            width: 260px;
            background: var(--dark-card);
            border-right: 1px solid var(--dark-border);
            position: fixed;
            height: 100vh;
            transition: var(--transition);
            z-index: 100;
        }
        
        .sidebar-header {
            padding: 1.5rem;
            border-bottom: 1px solid var(--dark-border);
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 1.3rem;
            font-weight: 600;
            color: var(--primary);
        }
        
        .logo i {
            color: var(--accent);
            font-size: 1.5rem;
        }
        
        .nav-links {
            padding: 1rem 0;
        }
        
        .nav-item {
            padding: 0.8rem 1.5rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            color: var(--gray-text);
            text-decoration: none;
            transition: var(--transition);
            cursor: pointer;
        }
        
        .nav-item:hover,
        .nav-item.active {
            background: rgba(0, 180, 216, 0.1);
            color: var(--primary);
            border-left: 3px solid var(--primary);
        }
        
        .nav-item i {
            width: 20px;
            text-align: center;
        }
        
        .user-info {
            position: absolute;
            bottom: 0;
            width: 100%;
            padding: 1.5rem;
            border-top: 1px solid var(--dark-border);
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        
        .user-avatar {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
        }
        
        /* Main Content */
        .main-content {
            flex: 1;
            margin-left: 260px;
            padding: 2rem;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--dark-border);
        }
        
        .header h1 {
            font-size: 1.8rem;
            font-weight: 600;
        }
        
        .logout-btn {
            background: var(--dark-card);
            border: 1px solid var(--dark-border);
            color: var(--light-text);
            padding: 0.5rem 1.5rem;
            border-radius: 8px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            transition: var(--transition);
        }
        
        .logout-btn:hover {
            background: var(--danger);
            border-color: var(--danger);
        }
        
        /* Stats Cards */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .stat-card {
            background: var(--dark-card);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--dark-border);
            transition: var(--transition);
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            border-color: var(--primary);
        }
        
        .stat-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .stat-icon {
            width: 50px;
            height: 50px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
        }
        
        .stat-icon.appointments { background: rgba(0, 180, 216, 0.1); color: var(--primary); }
        .stat-icon.pending { background: rgba(245, 158, 11, 0.1); color: var(--warning); }
        .stat-icon.today { background: rgba(16, 185, 129, 0.1); color: var(--success); }
        .stat-icon.cases { background: rgba(239, 68, 68, 0.1); color: var(--danger); }
        
        .stat-number {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        .stat-label {
            color: var(--gray-text);
            font-size: 0.9rem;
        }
        
        /* Tables */
        .card {
            background: var(--dark-card);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--dark-border);
            margin-bottom: 2rem;
        }
        
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }
        
        .card-title {
            font-size: 1.3rem;
            font-weight: 600;
        }
        
        .table-container {
            overflow-x: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th {
            text-align: left;
            padding: 1rem;
            color: var(--gray-text);
            font-weight: 500;
            border-bottom: 1px solid var(--dark-border);
        }
        
        td {
            padding: 1rem;
            border-bottom: 1px solid var(--dark-border);
        }
        
        tr:hover {
            background: rgba(255, 255, 255, 0.03);
        }
        
        .status {
            display: inline-block;
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
        }
        
        .status.pending { background: rgba(245, 158, 11, 0.1); color: var(--warning); }
        .status.confirmed { background: rgba(16, 185, 129, 0.1); color: var(--success); }
        .status.cancelled { background: rgba(239, 68, 68, 0.1); color: var(--danger); }
        
        .btn {
            padding: 0.5rem 1rem;
            border-radius: 6px;
            border: none;
            cursor: pointer;
            font-family: inherit;
            font-weight: 500;
            transition: var(--transition);
        }
        
        .btn-sm {
            padding: 0.3rem 0.8rem;
            font-size: 0.85rem;
        }
        
        .btn-primary {
            background: var(--primary);
            color: white;
        }
        
        .btn-primary:hover {
            background: var(--primary-dark);
        }
        
        .btn-success {
            background: var(--success);
            color: white;
        }
        
        .btn-danger {
            background: var(--danger);
            color: white;
        }
        
        .btn-outline {
            background: transparent;
            border: 1px solid var(--dark-border);
            color: var(--light-text);
        }
        
        .btn-outline:hover {
            border-color: var(--primary);
            color: var(--primary);
        }
        
        /* Gallery Grid */
        .gallery-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1.5rem;
        }
        
        .gallery-item {
            background: var(--dark-card);
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid var(--dark-border);
        }
        
        .gallery-image {
            height: 200px;
            overflow: hidden;
        }
        
        .gallery-image img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.5s ease;
        }
        
        .gallery-item:hover .gallery-image img {
            transform: scale(1.05);
        }
        
        .gallery-content {
            padding: 1rem;
        }
        
        .gallery-title {
            font-weight: 600;
            margin-bottom: 0.5rem;
        }
        
        .gallery-description {
            color: var(--gray-text);
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }
        
        /* Login Page */
        .login-container {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--dark-bg);
        }
        
        .login-box {
            width: 100%;
            max-width: 400px;
            background: var(--dark-card);
            padding: 2.5rem;
            border-radius: 16px;
            border: 1px solid var(--dark-border);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }
        
        .login-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .login-header .logo {
            justify-content: center;
            margin-bottom: 1rem;
            font-size: 1.5rem;
        }
        
        .login-header h2 {
            font-size: 1.8rem;
            margin-bottom: 0.5rem;
        }
        
        .login-header p {
            color: var(--gray-text);
        }
        
        .form-group {
            margin-bottom: 1.5rem;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            color: var(--gray-text);
            font-size: 0.9rem;
        }
        
        .form-control {
            width: 100%;
            padding: 0.8rem 1rem;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--dark-border);
            border-radius: 8px;
            color: var(--light-text);
            font-family: inherit;
            transition: var(--transition);
        }
        
        .form-control:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(0, 180, 216, 0.1);
        }
        
        .login-btn {
            width: 100%;
            padding: 1rem;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 8px;
            font-family: inherit;
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition);
            margin-top: 1rem;
        }
        
        .login-btn:hover {
            background: var(--primary-dark);
        }
        
        .alert {
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            display: none;
        }
        
        .alert-danger {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid var(--danger);
            color: var(--danger);
        }
        
        .alert-success {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid var(--success);
            color: var(--success);
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .sidebar {
                width: 70px;
            }
            
            .sidebar .nav-text,
            .sidebar .logo-text,
            .sidebar .user-name {
                display: none;
            }
            
            .main-content {
                margin-left: 70px;
            }
            
            .stats-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div id="login-container" class="login-container">
        <div class="login-box">
            <div class="login-header">
                <div class="logo">
                    <i class="fas fa-smile"></i>
                    <span class="logo-text">Savaş Smile</span>
                </div>
                <h2>Connexion Admin</h2>
                <p>Accès sécurisé au tableau de bord</p>
            </div>
            
            <div id="login-alert" class="alert alert-danger" style="display: none;">
                Identifiants incorrects. Veuillez réessayer.
            </div>
            
            <form id="login-form">
                <div class="form-group">
                    <label for="username">Nom d'utilisateur</label>
                    <input type="text" id="username" class="form-control" placeholder="admin" required>
                </div>
                
                <div class="form-group">
                    <label for="password">Mot de passe</label>
                    <input type="password" id="password" class="form-control" placeholder="••••••••" required>
                </div>
                
                <button type="submit" class="login-btn">
                    <i class="fas fa-sign-in-alt"></i> Se connecter
                </button>
            </form>
        </div>
    </div>
    
    <div id="admin-container" class="admin-container" style="display: none;">
        <!-- Sidebar -->
        <div class="sidebar">
            <div class="sidebar-header">
                <div class="logo">
                    <i class="fas fa-smile"></i>
                    <span class="logo-text">Savaş Smile</span>
                </div>
            </div>
            
            <div class="nav-links">
                <a class="nav-item active" data-tab="dashboard">
                    <i class="fas fa-tachometer-alt"></i>
                    <span class="nav-text">Dashboard</span>
                </a>
                <a class="nav-item" data-tab="appointments">
                    <i class="fas fa-calendar-check"></i>
                    <span class="nav-text">Rendez-vous</span>
                </a>
                <a class="nav-item" data-tab="gallery">
                    <i class="fas fa-images"></i>
                    <span class="nav-text">Galerie</span>
                </a>
                <a class="nav-item" data-tab="stats">
                    <i class="fas fa-chart-bar"></i>
                    <span class="nav-text">Statistiques</span>
                </a>
                <a class="nav-item" data-tab="settings">
                    <i class="fas fa-cog"></i>
                    <span class="nav-text">Paramètres</span>
                </a>
            </div>
            
            <div class="user-info">
                <div class="user-avatar" id="user-avatar">A</div>
                <div>
                    <div class="user-name" id="user-name">Administrateur</div>
                    <div class="user-role" style="color: var(--gray-text); font-size: 0.85rem;">Admin</div>
                </div>
            </div>
        </div>
        
        <!-- Main Content -->
        <div class="main-content">
            <div class="header">
                <h1 id="page-title">Dashboard</h1>
                <button class="logout-btn" onclick="logout()">
                    <i class="fas fa-sign-out-alt"></i> Déconnexion
                </button>
            </div>
            
            <!-- Dashboard Tab -->
            <div id="dashboard-tab" class="tab-content">
                <!-- Stats Cards -->
                <div class="stats-grid" id="stats-cards"></div>
                
                <!-- Recent Appointments -->
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">Rendez-vous récents</h3>
                        <button class="btn btn-outline" onclick="loadTab('appointments')">
                            Voir tout <i class="fas fa-arrow-right"></i>
                        </button>
                    </div>
                    <div class="table-container">
                        <table id="recent-appointments">
                            <thead>
                                <tr>
                                    <th>Patient</th>
                                    <th>Téléphone</th>
                                    <th>Date</th>
                                    <th>Traitement</th>
                                    <th>Statut</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody></tbody>
                        </table>
                    </div>
                </div>
                
                <!-- Gallery Preview -->
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">Derniers cas cliniques</h3>
                        <button class="btn btn-outline" onclick="loadTab('gallery')">
                            Gérer <i class="fas fa-arrow-right"></i>
                        </button>
                    </div>
                    <div class="gallery-grid" id="gallery-preview"></div>
                </div>
            </div>
            
            <!-- Appointments Tab -->
            <div id="appointments-tab" class="tab-content" style="display: none;">
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">Tous les rendez-vous</h3>
                        <div>
                            <select id="filter-status" class="form-control" style="display: inline-block; width: auto;" onchange="loadAppointments()">
                                <option value="">Tous les statuts</option>
                                <option value="pending">En attente</option>
                                <option value="confirmed">Confirmés</option>
                                <option value="cancelled">Annulés</option>
                            </select>
                        </div>
                    </div>
                    <div class="table-container">
                        <table id="all-appointments">
                            <thead>
                                <tr>
                                    <th>Patient</th>
                                    <th>Email</th>
                                    <th>Téléphone</th>
                                    <th>Date</th>
                                    <th>Traitement</th>
                                    <th>Message</th>
                                    <th>Statut</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody></tbody>
                        </table>
                    </div>
                </div>
            </div>
            
            <!-- Gallery Tab -->
            <div id="gallery-tab" class="tab-content" style="display: none;">
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">Gérer la galerie</h3>
                        <button class="btn btn-primary" onclick="showAddGalleryModal()">
                            <i class="fas fa-plus"></i> Ajouter un cas
                        </button>
                    </div>
                    <div class="gallery-grid" id="full-gallery"></div>
                </div>
            </div>
            
            <!-- Stats Tab -->
            <div id="stats-tab" class="tab-content" style="display: none;">
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">Statistiques</h3>
                    </div>
                    <div style="padding: 1rem;">
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 2rem;">
                            <div>
                                <h4 style="margin-bottom: 1rem;">Rendez-vous par mois</h4>
                                <canvas id="appointments-chart" height="200"></canvas>
                            </div>
                            <div>
                                <h4 style="margin-bottom: 1rem;">Répartition des traitements</h4>
                                <canvas id="treatments-chart" height="200"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Settings Tab -->
            <div id="settings-tab" class="tab-content" style="display: none;">
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">Paramètres</h3>
                    </div>
                    <div style="padding: 1rem;">
                        <h4 style="margin-bottom: 1rem;">Informations du compte</h4>
                        <div class="form-group">
                            <label>Nom d'utilisateur</label>
                            <input type="text" class="form-control" value="admin" disabled>
                        </div>
                        <div class="form-group">
                            <label>Email</label>
                            <input type="email" class="form-control" value="admin@savassmile.com">
                        </div>
                        <h4 style="margin: 2rem 0 1rem;">Changer le mot de passe</h4>
                        <div class="form-group">
                            <label>Nouveau mot de passe</label>
                            <input type="password" class="form-control" id="new-password">
                        </div>
                        <div class="form-group">
                            <label>Confirmer le mot de passe</label>
                            <input type="password" class="form-control" id="confirm-password">
                        </div>
                        <button class="btn btn-primary" onclick="updatePassword()">
                            <i class="fas fa-save"></i> Enregistrer les modifications
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Add Gallery Modal -->
    <div id="add-gallery-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; align-items: center; justify-content: center;">
        <div style="background: var(--dark-card); padding: 2rem; border-radius: 12px; width: 90%; max-width: 500px; border: 1px solid var(--dark-border);">
            <h3 style="margin-bottom: 1.5rem;">Ajouter un cas clinique</h3>
            <div class="form-group">
                <label>Titre</label>
                <input type="text" class="form-control" id="gallery-title">
            </div>
            <div class="form-group">
                <label>Description</label>
                <textarea class="form-control" id="gallery-description" rows="3"></textarea>
            </div>
            <div class="form-group">
                <label>URL image avant</label>
                <input type="text" class="form-control" id="gallery-before">
            </div>
            <div class="form-group">
                <label>URL image après</label>
                <input type="text" class="form-control" id="gallery-after">
            </div>
            <div class="form-group">
                <label>Catégorie</label>
                <select class="form-control" id="gallery-category">
                    <option value="Invisalign">Invisalign</option>
                    <option value="Blanchiment">Blanchiment</option>
                    <option value="Implant">Implant</option>
                    <option value="Autre">Autre</option>
                </select>
            </div>
            <div class="form-group">
                <label>Durée du traitement</label>
                <input type="text" class="form-control" id="gallery-duration" placeholder="Ex: 6 mois">
            </div>
            <div style="display: flex; gap: 1rem; margin-top: 2rem;">
                <button class="btn btn-primary" style="flex: 1;" onclick="addGalleryItem()">
                    <i class="fas fa-plus"></i> Ajouter
                </button>
                <button class="btn btn-outline" style="flex: 1;" onclick="closeModal()">
                    Annuler
                </button>
            </div>
        </div>
    </div>
    
    <script>
        const ADMIN_PATH = "{{ admin_path }}";
        let currentUser = '';
        
        // Login
        document.getElementById('login-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            const response = await fetch(`/${ADMIN_PATH}/login`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (data.success) {
                currentUser = username;
                document.getElementById('login-container').style.display = 'none';
                document.getElementById('admin-container').style.display = 'flex';
                document.getElementById('user-name').textContent = username;
                document.getElementById('user-avatar').textContent = username.charAt(0).toUpperCase();
                loadDashboard();
            } else {
                document.getElementById('login-alert').style.display = 'block';
                setTimeout(() => {
                    document.getElementById('login-alert').style.display = 'none';
                }, 3000);
            }
        });
        
        // Navigation
        function loadTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.style.display = 'none';
            });
            
            // Remove active class from all nav items
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(`${tabName}-tab`).style.display = 'block';
            
            // Add active class to clicked nav item
            document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
            
            // Update page title
            const titles = {
                'dashboard': 'Dashboard',
                'appointments': 'Rendez-vous',
                'gallery': 'Galerie',
                'stats': 'Statistiques',
                'settings': 'Paramètres'
            };
            document.getElementById('page-title').textContent = titles[tabName];
            
            // Load data for tab
            if (tabName === 'appointments') loadAppointments();
            if (tabName === 'gallery') loadGallery();
            if (tabName === 'stats') loadStats();
        }
        
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', function() {
                loadTab(this.dataset.tab);
            });
        });
        
        // Dashboard
        async function loadDashboard() {
            const response = await fetch(`/${ADMIN_PATH}/dashboard`);
            const data = await response.json();
            
            // Update stats cards
            document.getElementById('stats-cards').innerHTML = `
                <div class="stat-card">
                    <div class="stat-header">
                        <div>
                            <div class="stat-number">${data.stats.total_appointments}</div>
                            <div class="stat-label">RDV total</div>
                        </div>
                        <div class="stat-icon appointments">
                            <i class="fas fa-calendar-check"></i>
                        </div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-header">
                        <div>
                            <div class="stat-number">${data.stats.pending_appointments}</div>
                            <div class="stat-label">En attente</div>
                        </div>
                        <div class="stat-icon pending">
                            <i class="fas fa-clock"></i>
                        </div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-header">
                        <div>
                            <div class="stat-number">${data.stats.today_appointments}</div>
                            <div class="stat-label">Aujourd'hui</div>
                        </div>
                        <div class="stat-icon today">
                            <i class="fas fa-calendar-day"></i>
                        </div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-header">
                        <div>
                            <div class="stat-number">${data.stats.total_cases}</div>
                            <div class="stat-label">Cas cliniques</div>
                        </div>
                        <div class="stat-icon cases">
                            <i class="fas fa-images"></i>
                        </div>
                    </div>
                </div>
            `;
            
            // Update recent appointments
            const tbody = document.querySelector('#recent-appointments tbody');
            tbody.innerHTML = data.appointments.map(app => `
                <tr>
                    <td>${app.full_name}</td>
                    <td>${app.phone}</td>
                    <td>${app.appointment_date}<br><small>${app.appointment_time}</small></td>
                    <td>${app.treatment_type}</td>
                    <td><span class="status ${app.status}">${app.status}</span></td>
                    <td>
                        ${app.status === 'pending' ? `
                            <button class="btn btn-success btn-sm" onclick="confirmAppointment(${app.id})">Confirmer</button>
                            <button class="btn btn-danger btn-sm" onclick="cancelAppointment(${app.id})">Annuler</button>
                        ` : ''}
                    </td>
                </tr>
            `).join('');
            
            // Update gallery preview
            document.getElementById('gallery-preview').innerHTML = data.gallery.map(item => `
                <div class="gallery-item">
                    <div class="gallery-image">
                        <img src="${item.before_image}" alt="${item.title}">
                    </div>
                    <div class="gallery-content">
                        <div class="gallery-title">${item.title}</div>
                        <div class="gallery-description">${item.description}</div>
                        <div style="color: var(--gray-text); font-size: 0.85rem;">
                            <i class="fas fa-tag"></i> ${item.category} • ${item.treatment_duration}
                        </div>
                    </div>
                </div>
            `).join('');
        }
        
        // Appointments
        async function loadAppointments() {
            const statusFilter = document.getElementById('filter-status').value;
            let url = `/${ADMIN_PATH}/appointments`;
            
            const response = await fetch(url);
            const appointments = await response.json();
            
            const filteredAppointments = statusFilter 
                ? appointments.filter(app => app.status === statusFilter)
                : appointments;
            
            const tbody = document.querySelector('#all-appointments tbody');
            tbody.innerHTML = filteredAppointments.map(app => `
                <tr>
                    <td>${app.full_name}</td>
                    <td>${app.email}</td>
                    <td>${app.phone}</td>
                    <td>${app.appointment_date}<br><small>${app.appointment_time}</small></td>
                    <td>${app.treatment_type}</td>
                    <td style="max-width: 200px;">${app.message || '-'}</td>
                    <td><span class="status ${app.status}">${app.status}</span></td>
                    <td>
                        ${app.status === 'pending' ? `
                            <button class="btn btn-success btn-sm" onclick="confirmAppointment(${app.id})">Confirmer</button>
                            <button class="btn btn-danger btn-sm" onclick="cancelAppointment(${app.id})">Annuler</button>
                        ` : ''}
                    </td>
                </tr>
            `).join('');
        }
        
        async function confirmAppointment(id) {
            await fetch(`/${ADMIN_PATH}/appointment/${id}/confirm`, { method: 'POST' });
            loadDashboard();
            if (document.getElementById('appointments-tab').style.display !== 'none') {
                loadAppointments();
            }
        }
        
        async function cancelAppointment(id) {
            await fetch(`/${ADMIN_PATH}/appointment/${id}/cancel`, { method: 'POST' });
            loadDashboard();
            if (document.getElementById('appointments-tab').style.display !== 'none') {
                loadAppointments();
            }
        }
        
        // Gallery
        async function loadGallery() {
            const response = await fetch(`/${ADMIN_PATH}/gallery`);
            const gallery = await response.json();
            
            document.getElementById('full-gallery').innerHTML = gallery.map(item => `
                <div class="gallery-item">
                    <div class="gallery-image">
                        <img src="${item.before_image}" alt="${item.title}">
                    </div>
                    <div class="gallery-content">
                        <div class="gallery-title">${item.title}</div>
                        <div class="gallery-description">${item.description}</div>
                        <div style="color: var(--gray-text); font-size: 0.85rem; margin-bottom: 1rem;">
                            <i class="fas fa-tag"></i> ${item.category} • ${item.treatment_duration}
                        </div>
                        <button class="btn btn-danger btn-sm" onclick="deleteGalleryItem(${item.id})">
                            <i class="fas fa-trash"></i> Supprimer
                        </button>
                    </div>
                </div>
            `).join('');
        }
        
        function showAddGalleryModal() {
            document.getElementById('add-gallery-modal').style.display = 'flex';
        }
        
        function closeModal() {
            document.getElementById('add-gallery-modal').style.display = 'none';
        }
        
        async function addGalleryItem() {
            const item = {
                title: document.getElementById('gallery-title').value,
                description: document.getElementById('gallery-description').value,
                before_image: document.getElementById('gallery-before').value,
                after_image: document.getElementById('gallery-after').value,
                category: document.getElementById('gallery-category').value,
                treatment_duration: document.getElementById('gallery-duration').value
            };
            
            const response = await fetch(`/${ADMIN_PATH}/gallery`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(item)
            });
            
            const data = await response.json();
            
            if (data.success) {
                closeModal();
                loadGallery();
                loadDashboard();
            }
        }
        
        async function deleteGalleryItem(id) {
            if (confirm('Supprimer ce cas de la galerie ?')) {
                await fetch(`/${ADMIN_PATH}/gallery/${id}`, { method: 'DELETE' });
                loadGallery();
                loadDashboard();
            }
        }
        
        // Statistics
        async function loadStats() {
            const response = await fetch(`/${ADMIN_PATH}/dashboard`);
            const data = await response.json();
            
            // Simple chart data for demo
            const ctx1 = document.getElementById('appointments-chart').getContext('2d');
            const chart1 = new Chart(ctx1, {
                type: 'line',
                data: {
                    labels: data.charts.appointments_by_month.map(item => item.month),
                    datasets: [{
                        label: 'Rendez-vous',
                        data: data.charts.appointments_by_month.map(item => item.count),
                        borderColor: '#00b4d8',
                        backgroundColor: 'rgba(0, 180, 216, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255,255,255,0.1)' },
                            ticks: { color: '#94a3b8' }
                        },
                        x: {
                            grid: { color: 'rgba(255,255,255,0.1)' },
                            ticks: { color: '#94a3b8' }
                        }
                    }
                }
            });
            
            // Simple pie chart for demo
            const ctx2 = document.getElementById('treatments-chart').getContext('2d');
            const chart2 = new Chart(ctx2, {
                type: 'doughnut',
                data: {
                    labels: ['Invisalign', 'Blanchiment', 'Implant', 'Consultation'],
                    datasets: [{
                        data: [45, 25, 15, 15],
                        backgroundColor: [
                            '#00b4d8',
                            '#ff6b6b',
                            '#ffd166',
                            '#10b981'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: '#94a3b8' }
                        }
                    }
                }
            });
        }
        
        // Settings
        async function updatePassword() {
            const newPassword = document.getElementById('new-password').value;
            const confirmPassword = document.getElementById('confirm-password').value;
            
            if (newPassword !== confirmPassword) {
                alert('Les mots de passe ne correspondent pas.');
                return;
            }
            
            alert('Fonctionnalité à implémenter - changement de mot de passe');
        }
        
        // Logout
        async function logout() {
            await fetch(`/${ADMIN_PATH}/logout`, { method: 'POST' });
            document.getElementById('admin-container').style.display = 'none';
            document.getElementById('login-container').style.display = 'flex';
            document.getElementById('username').value = '';
            document.getElementById('password').value = '';
        }
        
        // Auto-refresh every 30 seconds
        setInterval(() => {
            if (document.getElementById('dashboard-tab').style.display !== 'none') {
                loadDashboard();
            }
        }, 30000);
    </script>
</body>
</html>
'''

@app.route(f'/{app.config["ADMIN_PATH"]}/page')
def admin_page():
    return render_template_string(ADMIN_PAGE, admin_path=app.config['ADMIN_PATH'])

# ==================== LANCEMENT ====================

if __name__ == '__main__':
    print("=" * 70)
    print("🚀 SAVAŞ SMILE - VERSION PROFESSIONNELLE")
    print("=" * 70)
    print(f"\n🌐 SITE PUBLIC : http://localhost:5000")
    print(f"🔐 PAGE ADMIN : http://localhost:5000/{app.config['ADMIN_PATH']}/page")
    print(f"🔑 IDENTIFIANTS : admin / Admin@2024")
    print("\n✨ NOUVELLES FONCTIONNALITÉS :")
    print("   • Interface admin design sombre moderne")
    print("   • Dashboard avec statistiques en temps réel")
    print("   • Graphiques interactifs")
    print("   • Gestion complète galerie")
    print("   • Navigation fluide avec sidebar")
    print("\n⏹️  Pour arrêter : Ctrl+C")
    print("=" * 70)
    
    app.run(debug=True, use_reloader=False, port=5000)