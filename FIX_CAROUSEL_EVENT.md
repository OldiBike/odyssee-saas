# Correction du Carousel pour les Événements

## Diagnostic

❌ **PROBLÈME IDENTIFIÉ**: Le carousel pour les images d'événements n'a JAMAIS été implémenté dans `services/template_engine.py`.

### Situation actuelle
- Les images s'affichent empilées verticalement
- Pas de navigation entre les images
- Pas d'indicateurs
- Aucun CSS ou JavaScript de carousel n'existe

### Cause
- Erreur de communication dans une conversation précédente
- Le code du carousel n'a jamais été ajouté au fichier

## Solution

Il faut ajouter 3 éléments au template généré :

1. **HTML du carousel** avec navigation et indicateurs
2. **CSS** pour le style du carousel
3. **JavaScript** pour la fonctionnalité

## Implémentation

### 1. Structure HTML du carousel
```html
<div class="event-carousel">
    <div class="event-carousel-container">
        <div class="event-carousel-track">
            <!-- Images ici -->
        </div>
        <!-- Boutons de navigation (si plusieurs images) -->
        <button class="event-carousel-btn event-carousel-prev">‹</button>
        <button class="event-carousel-btn event-carousel-next">›</button>
    </div>
    <!-- Indicateurs (si plusieurs images) -->
    <div class="event-carousel-indicators">
        <!-- Points indicateurs ici -->
    </div>
</div>
```

### 2. CSS à ajouter
```css
/* Event Carousel */
.event-carousel {
    position: relative;
    width: 100%;
    margin: 1rem 0;
}

.event-carousel-container {
    position: relative;
    overflow: hidden;
    border-radius: 15px;
}

.event-carousel-track {
    display: flex;
    transition: transform 0.3s ease-in-out;
}

.event-carousel-item {
    min-width: 100%;
    box-sizing: border-box;
}

.event-carousel-item img {
    width: 100%;
    height: 300px;
    object-fit: cover;
    display: block;
}

.event-carousel-btn {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(0, 0, 0, 0.5);
    color: white;
    border: none;
    font-size: 2rem;
    padding: 0.5rem 1rem;
    cursor: pointer;
    z-index: 10;
    transition: background 0.3s;
}

.event-carousel-btn:hover {
    background: rgba(0, 0, 0, 0.7);
}

.event-carousel-prev {
    left: 10px;
}

.event-carousel-next {
    right: 10px;
}

.event-carousel-indicators {
    display: flex;
    justify-content: center;
    gap: 8px;
    margin-top: 1rem;
}

.event-carousel-indicator {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #d1d5db;
    border: none;
    cursor: pointer;
    transition: background 0.3s;
}

.event-carousel-indicator.active {
    background: #3b82f6;
}
```

### 3. JavaScript à ajouter
```javascript
// Event Carousel functionality
(function() {
    const carousel = document.querySelector('.event-carousel');
    if (!carousel) return;
    
    const track = carousel.querySelector('.event-carousel-track');
    const items = carousel.querySelectorAll('.event-carousel-item');
    const prevBtn = carousel.querySelector('.event-carousel-prev');
    const nextBtn = carousel.querySelector('.event-carousel-next');
    const indicators = carousel.querySelectorAll('.event-carousel-indicator');
    
    if (items.length <= 1) return; // Pas besoin de carousel pour 1 image
    
    let currentIndex = 0;
    
    function updateCarousel() {
        track.style.transform = `translateX(-${currentIndex * 100}%)`;
        indicators.forEach((ind, i) => {
            ind.classList.toggle('active', i === currentIndex);
        });
    }
    
    function nextSlide() {
        currentIndex = (currentIndex + 1) % items.length;
        updateCarousel();
    }
    
    function prevSlide() {
        currentIndex = (currentIndex - 1 + items.length) % items.length;
        updateCarousel();
    }
    
    function goToSlide(index) {
        currentIndex = index;
        updateCarousel();
    }
    
    if (prevBtn) prevBtn.addEventListener('click', prevSlide);
    if (nextBtn) nextBtn.addEventListener('click', nextSlide);
    
    indicators.forEach((indicator, index) => {
        indicator.addEventListener('click', () => goToSlide(index));
    });
})();
```

## Étapes de correction

1. ✅ Restaurer le fichier `template_engine.py` depuis Git
2. ⏳ Modifier le code pour ajouter le carousel
3. ⏳ Tester avec une fiche contenant plusieurs images d'événement

## Impact

Cette correction permettra :
- ✅ Navigation fluide entre les images d'événements
- ✅ Indicateurs visuels pour la position
- ✅ Interface utilisateur moderne et intuitive
- ✅ Affichage propre sur mobile et desktop
