// ============================================================================
// WIZARD.JS - Système de Génération de Voyage avec IA Conversationnelle
// Version: 1.0
// Date: 14 Octobre 2025
// ============================================================================

/**
 * Classe principale du Wizard de génération de voyage
 * Gère le flux conversationnel étape par étape avec pré-remplissage IA
 */
class TravelWizard {
    constructor() {
        this.currentStep = 0;
        this.totalSteps = 0;
        this.wizardData = {};
        this.parsedPrompt = null;
        this.steps = [];
        this.isInitialized = false;
    }

    /**
     * Initialise le wizard et commence le processus
     */
    async init() {
        if (this.isInitialized) return;

        // Attacher les événements globaux
        this.attachGlobalEvents();
        
        this.isInitialized = true;
        console.log('✅ Wizard initialisé');
    }

    /**
     * Attache les événements aux boutons principaux
     */
    attachGlobalEvents() {
        // Bouton démarrer le wizard
        const startBtn = document.getElementById('start-wizard-btn');
        if (startBtn) {
            startBtn.addEventListener('click', () => this.startWizard());
        }

        // Bouton mode manuel
        const manualBtn = document.getElementById('skip-to-form-btn');
        if (manualBtn) {
            manualBtn.addEventListener('click', () => this.switchToManualMode());
        }

        // Toggle mode IA/Manuel
        const tabs = document.querySelectorAll('.tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                const mode = e.target.dataset.mode;
                this.switchMode(mode);
            });
        });

        // Navigation wizard
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');
        const skipBtn = document.getElementById('skip-btn');

        if (prevBtn) prevBtn.addEventListener('click', () => this.prevStep());
        if (nextBtn) nextBtn.addEventListener('click', () => this.nextStep());
        if (skipBtn) skipBtn.addEventListener('click', () => this.skipStep());

        // Exemples de prompts
        const exampleBtns = document.querySelectorAll('.example-btn');
        exampleBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.getElementById('ai-prompt').value = e.target.textContent.trim();
            });
        });
    }

    /**
     * Change le mode (IA ou Manuel)
     */
    switchMode(mode) {
        const tabs = document.querySelectorAll('.tab');
        const aiMode = document.getElementById('ai-mode');
        const manualMode = document.getElementById('manual-mode');

        tabs.forEach(t => t.classList.remove('active'));
        document.querySelector(`[data-mode="${mode}"]`).classList.add('active');

        if (mode === 'ai') {
            aiMode.style.display = 'block';
            manualMode.style.display = 'none';
        } else {
            aiMode.style.display = 'none';
            manualMode.style.display = 'block';
        }
    }

    /**
     * Passe en mode formulaire manuel complet
     */
    switchToManualMode() {
        alert('Mode manuel : formulaire complet (à implémenter)');
        // TODO: Afficher le formulaire complet classique
    }

    /**
     * Démarre le wizard avec parsing du prompt
     */
    async startWizard() {
        const prompt = document.getElementById('ai-prompt').value.trim();

        if (!prompt) {
            this.showError('Veuillez décrire votre voyage');
            return;
        }

        this.showLoading('🤖 Analyse de votre demande...');

        try {
            // Appel API pour parser le prompt
            const response = await fetch('/api/ai-parse-prompt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
            });

            const data = await response.json();

            if (!data.success) {
                this.hideLoading();
                this.showError(data.error || 'Erreur lors de l\'analyse');
                return;
            }

            this.parsedPrompt = data;
            console.log('✅ Prompt parsé:', data);

            // Générer les étapes du wizard
            this.steps = this.generateSteps(data);
            this.totalSteps = this.steps.length;

            // Initialiser les données du wizard avec les valeurs parsées
            this.wizardData = { ...data };

            // Afficher le wizard
            this.hideLoading();
            this.showWizardContainer();
            this.showStep(0);

        } catch (error) {
            console.error('❌ Erreur:', error);
            this.hideLoading();
            this.showError('Erreur de connexion au serveur');
        }
    }

    /**
     * Génère la liste des étapes selon le type de voyage
     */
    generateSteps(parsedData) {
        const steps = [];

        // Étape 1 : Hôtel (sauf si voyage d'un jour)
        if (!parsedData.is_day_trip) {
            steps.push({
                id: 'hotel',
                title: '🏨 Quel hôtel ?',
                prefilled: parsedData.hotel_name || '',
                hint: parsedData.destination ? `L'IA a détecté : ${parsedData.destination}` : ''
            });
        }

        // Étape 2 : Destination
        steps.push({
            id: 'destination',
            title: '📍 Confirmez la destination',
            prefilled: parsedData.destination || ''
        });

        // Étape 3 : Lieux d'intérêt
        steps.push({
            id: 'activities',
            title: '🎯 Lieux d\'intérêt',
            prefilled: parsedData.activities || []
        });

        // Étape 4 : Transport
        steps.push({
            id: 'transport',
            title: '🚌 Transport',
            prefilled: parsedData.transport_type || '',
            requiresExtraFields: parsedData.transport_type === 'autocar'
        });

        // Étape 5 : Type de séjour
        steps.push({
            id: 'trip_type',
            title: '📅 Type de séjour',
            prefilled: { is_day_trip: parsedData.is_day_trip || false }
        });

        // Étapes conditionnelles selon le type
        if (parsedData.is_day_trip) {
            // Voyage d'un jour
            steps.push(
                { id: 'schedule', title: '⏰ Horaires', prefilled: {} },
                { id: 'program', title: '📋 Programme de la journée', prefilled: [] },
                { id: 'pricing', title: '💰 Prix & Inclus', prefilled: { price: parsedData.price || null } }
            );
        } else {
            // Séjour normal
            steps.push(
                { id: 'dates', title: '🗓️ Dates du séjour', prefilled: { duration: parsedData.estimated_duration || 3 } },
                { id: 'stars', title: '⭐ Catégorie de l\'hôtel', prefilled: parsedData.stars || 3 },
                { id: 'meal_plan', title: '🍽️ Formule repas', prefilled: parsedData.meal_plan || 'petit_dejeuner' },
                { id: 'pricing', title: '💰 Prix & Services', prefilled: { price: parsedData.price || null } }
            );
        }

        // Étape finale : Récapitulatif
        steps.push({
            id: 'summary',
            title: '✅ Récapitulatif'
        });

        return steps;
    }

    /**
     * Affiche une étape du wizard
     */
    showStep(stepIndex) {
        this.currentStep = stepIndex;
        const step = this.steps[stepIndex];

        // Mettre à jour la barre de progression
        const progress = ((stepIndex + 1) / this.totalSteps) * 100;
        const progressBar = document.querySelector('.progress-fill');
        const progressText = document.querySelector('.progress-text');

        if (progressBar) progressBar.style.width = `${progress}%`;
        if (progressText) progressText.textContent = `Étape ${stepIndex + 1}/${this.totalSteps}`;

        // Afficher le contenu de l'étape
        const container = document.getElementById('current-step-container');
        if (container) {
            container.innerHTML = this.renderStep(step);
        }

        // Initialiser les événements de l'étape
        this.initStepListeners(step);

        // Gérer les boutons de navigation
        this.updateNavigationButtons(stepIndex);

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    /**
     * Génère le HTML d'une étape
     */
    renderStep(step) {
        switch (step.id) {
            case 'hotel':
                return this.renderHotelStep(step);
            case 'destination':
                return this.renderDestinationStep(step);
            case 'activities':
                return this.renderActivitiesStep(step);
            case 'transport':
                return this.renderTransportStep(step);
            case 'trip_type':
                return this.renderTripTypeStep(step);
            case 'schedule':
                return this.renderScheduleStep(step);
            case 'program':
                return this.renderProgramStep(step);
            case 'dates':
                return this.renderDatesStep(step);
            case 'stars':
                return this.renderStarsStep(step);
            case 'meal_plan':
                return this.renderMealPlanStep(step);
            case 'pricing':
                return this.renderPricingStep(step);
            case 'summary':
                return this.renderSummaryStep();
            default:
                return '<p>Étape en construction</p>';
        }
    }

    /**
     * Rendu de l'étape Hôtel
     */
    renderHotelStep(step) {
        return `
            <div class="wizard-step-content">
                <h2>${step.title}</h2>
                ${step.hint ? `<p class="hint">${step.hint}</p>` : ''}
                
                <div class="form-group">
                    <label for="hotel_name">Nom de l'hôtel</label>
                    <input 
                        type="text" 
                        id="hotel_name" 
                        class="form-control"
                        placeholder="Ex: Hotel Colosseo, Hôtel de Paris..."
                        value="${this.escapeHtml(step.prefilled)}"
                    />
                    <small class="text-muted">Laissez vide si vous ne connaissez pas encore le nom</small>
                </div>
            </div>
        `;
    }

    /**
     * Rendu de l'étape Destination
     */
    renderDestinationStep(step) {
        return `
            <div class="wizard-step-content">
                <h2>${step.title}</h2>
                <p class="hint">Vérifiez et modifiez si nécessaire</p>
                
                <div class="form-group">
                    <label for="destination">Destination</label>
                    <input 
                        type="text" 
                        id="destination" 
                        class="form-control"
                        placeholder="Ex: Rome, Italie"
                        value="${this.escapeHtml(step.prefilled)}"
                        required
                    />
                </div>
            </div>
        `;
    }

    /**
     * Rendu de l'étape Lieux d'intérêt
     */
    renderActivitiesStep(step) {
        const activities = step.prefilled || [];

        return `
            <div class="wizard-step-content">
                <h2>${step.title}</h2>
                ${activities.length > 0 ? '<p class="hint">L\'IA a détecté ces activités :</p>' : '<p class="hint">Ajoutez les lieux que vous souhaitez visiter</p>'}
                
                <div id="activities-list" class="activities-list">
                    ${activities.map((activity, index) => `
                        <div class="activity-item" data-index="${index}">
                            <span class="activity-drag-handle">⋮⋮</span>
                            <input 
                                type="text" 
                                class="form-control activity-name" 
                                value="${this.escapeHtml(activity)}"
                                placeholder="Nom du lieu"
                            />
                            <button type="button" class="btn-icon delete-activity" data-index="${index}">
                                🗑️
                            </button>
                        </div>
                    `).join('')}
                </div>
                
                <button type="button" id="add-activity-btn" class="btn btn-secondary mt-3">
                    ➕ Ajouter un lieu d'intérêt
                </button>
            </div>
        `;
    }

    /**
     * Rendu de l'étape Transport
     */
    renderTransportStep(step) {
        const transports = [
            { value: 'avion', label: '✈️ Avion', icon: '✈️' },
            { value: 'train', label: '🚂 Train', icon: '🚂' },
            { value: 'autocar', label: '🚌 Autocar', icon: '🚌' },
            { value: 'voiture', label: '🚗 Voiture', icon: '🚗' }
        ];

        const selected = step.prefilled || 'avion';
        const showAutocarFields = selected === 'autocar';

        return `
            <div class="wizard-step-content">
                <h2>${step.title}</h2>
                <p class="hint">Choisissez le moyen de transport</p>
                
                <div class="transport-options">
                    ${transports.map(t => `
                        <label class="radio-card ${selected === t.value ? 'checked' : ''}">
                            <input 
                                type="radio" 
                                name="transport" 
                                value="${t.value}"
                                ${selected === t.value ? 'checked' : ''}
                            />
                            <span class="radio-card-content">
                                <span class="radio-icon">${t.icon}</span>
                                <span class="radio-label">${t.label.replace(t.icon + ' ', '')}</span>
                            </span>
                        </label>
                    `).join('')}
                </div>
                
                <div id="autocar-fields" class="autocar-fields mt-4" style="display: ${showAutocarFields ? 'block' : 'none'}">
                    <h3 class="h5">📍 Informations autocar</h3>
                    
                    <div class="form-group">
                        <label for="bus_departure_address">Point de départ</label>
                        <input 
                            type="text" 
                            id="bus_departure_address" 
                            class="form-control"
                            placeholder="Ex: Place de la Gare, Bruxelles"
                            value="${this.wizardData.bus_departure_address || ''}"
                        />
                    </div>
                    
                    <div class="form-group">
                        <label>Durée estimée du trajet</label>
                        <div class="duration-input">
                            <input 
                                type="number" 
                                id="travel_hours" 
                                class="form-control"
                                min="0" 
                                max="48" 
                                value="${this.wizardData.travel_hours || 0}"
                                style="width: 80px;"
                            />
                            <span>heures</span>
                            <input 
                                type="number" 
                                id="travel_minutes" 
                                class="form-control"
                                min="0" 
                                max="59" 
                                value="${this.wizardData.travel_minutes || 0}"
                                style="width: 80px;"
                            />
                            <span>minutes</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Rendu de l'étape Type de séjour
     */
    renderTripTypeStep(step) {
        const isDayTrip = step.prefilled?.is_day_trip || false;

        return `
            <div class="wizard-step-content">
                <h2>${step.title}</h2>
                <p class="hint">Sélectionnez le type de voyage</p>
                
                <div class="trip-type-options">
                    <label class="checkbox-card ${isDayTrip ? 'checked' : ''}">
                        <input 
                            type="checkbox" 
                            id="is_day_trip"
                            ${isDayTrip ? 'checked' : ''}
                        />
                        <div class="card-content">
                            <span class="icon">🌅</span>
                            <span class="title">Voyage d'un jour</span>
                            <span class="subtitle">Excursion sans nuitée</span>
                        </div>
                    </label>
                    
                    <label class="checkbox-card ${!isDayTrip ? 'checked' : ''}">
                        <input 
                            type="checkbox" 
                            id="is_multi_day"
                            ${!isDayTrip ? 'checked' : ''}
                        />
                        <div class="card-content">
                            <span class="icon">🏨</span>
                            <span class="title">Séjour avec hébergement</span>
                            <span class="subtitle">Une ou plusieurs nuits</span>
                        </div>
                    </label>
                </div>
                
                <div id="day-trip-fields" class="day-trip-fields mt-4" style="display: ${isDayTrip ? 'block' : 'none'}">
                    <h3 class="h5">⏰ Horaires</h3>
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="departure_time">Heure de départ</label>
                                <input 
                                    type="time" 
                                    id="departure_time" 
                                    class="form-control"
                                    value="${this.wizardData.departure_time || '08:00'}"
                                />
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label for="return_time">Heure de retour</label>
                                <input 
                                    type="time" 
                                    id="return_time" 
                                    class="form-control"
                                    value="${this.wizardData.return_time || '20:00'}"
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Rendu de l'étape Horaires (voyage 1 jour)
     */
    renderScheduleStep(step) {
        return `
            <div class="wizard-step-content">
                <h2>${step.title}</h2>
                <p class="hint">Définissez les horaires de votre excursion</p>
                
                <div class="row">
                    <div class="col-md-6">
                        <div class="form-group">
                            <label for="departure_time_confirm">Heure de départ</label>
                            <input 
                                type="time" 
                                id="departure_time_confirm" 
                                class="form-control"
                                value="${this.wizardData.departure_time || '08:00'}"
                            />
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="form-group">
                            <label for="return_time_confirm">Heure de retour</label>
                            <input 
                                type="time" 
                                id="return_time_confirm" 
                                class="form-control"
                                value="${this.wizardData.return_time || '20:00'}"
                            />
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Rendu de l'étape Programme (voyage 1 jour)
     */
    renderProgramStep(step) {
        const program = this.wizardData.program || [];

        return `
            <div class="wizard-step-content">
                <h2>${step.title}</h2>
                <p class="hint">Programme horaire de votre journée</p>
                
                ${program.length === 0 ? `
                    <div class="alert alert-info">
                        <p>Souhaitez-vous générer automatiquement un programme avec l'IA ?</p>
                        <button type="button" id="generate-program-btn" class="btn btn-primary">
                            ✨ Générer le programme automatiquement
                        </button>
                    </div>
                ` : ''}
                
                <div id="program-timeline" class="program-timeline">
                    ${program.map((item, index) => `
                        <div class="timeline-item" data-index="${index}">
                            <div class="timeline-time">${item.time}</div>
                            <div class="timeline-content">${this.escapeHtml(item.activity)}</div>
                        </div>
                    `).join('')}
                </div>
                
                ${program.length > 0 ? `
                    <button type="button" id="regenerate-program-btn" class="btn btn-secondary mt-3">
                        🔄 Régénérer le programme
                    </button>
                ` : ''}
            </div>
        `;
    }

    /**
     * Rendu de l'étape Dates
     */
    renderDatesStep(step) {
        const today = new Date().toISOString().split('T')[0];
        const duration = step.prefilled?.duration || 3;

        return `
            <div class="wizard-step-content">
                <h2>${step.title}</h2>
                <p class="hint">Quand souhaitez-vous partir ?</p>
                
                <div class="row">
                    <div class="col-md-6">
                        <div class="form-group">
                            <label for="date_start">Date de départ</label>
                            <input 
                                type="date" 
                                id="date_start" 
                                class="form-control"
                                min="${today}"
                                value="${this.wizardData.date_start || ''}"
                            />
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="form-group">
                            <label for="date_end">Date de retour</label>
                            <input 
                                type="date" 
                                id="date_end" 
                                class="form-control"
                                min="${today}"
                                value="${this.wizardData.date_end || ''}"
                            />
                        </div>
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="num_people">Nombre de personnes</label>
                    <div class="number-input">
                        <button type="button" class="btn-number" data-action="minus">-</button>
                        <input 
                            type="number" 
                            id="num_people" 
                            class="form-control"
                            min="1" 
                            max="20" 
                            value="${this.wizardData.num_people || 2}"
                        />
                        <button type="button" class="btn-number" data-action="plus">+</button>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Rendu de l'étape Catégorie
     */
    renderStarsStep(step) {
        const stars = step.prefilled || 3;

        return `
            <div class="wizard-step-content">
                <h2>${step.title}</h2>
                <p class="hint">Quelle catégorie d'hôtel souhaitez-vous ?</p>
                
                <div class="stars-selector">
                    ${[1, 2, 3, 4, 5].map(s => `
                        <label class="star-option ${s === stars ? 'selected' : ''}">
                            <input 
                                type="radio" 
                                name="stars" 
                                value="${s}"
                                ${s === stars ? 'checked' : ''}
                            />
                            <div class="star-content">
                                <div class="star-icons">${'⭐'.repeat(s)}</div>
                                <div class="star-label">${s} étoile${s > 1 ? 's' : ''}</div>
                            </div>
                        </label>
                    `).join('')}
                </div>
            </div>
        `;
    }

    /**
     * Rendu de l'étape Formule repas
     */
    renderMealPlanStep(step) {
        const mealPlans = [
            { value: 'logement_seul', label: '🔑 Logement seul', desc: 'Sans repas' },
            { value: 'petit_dejeuner', label: '☕ Petit-déjeuner', desc: 'Petit-déjeuner inclus' },
            { value: 'demi_pension', label: '🍽️ Demi-pension', desc: 'Petit-déj + dîner' },
            { value: 'pension_complete', label: '🍴 Pension complète', desc: 'Tous les repas' },
            { value: 'all_in', label: '🎉 All Inclusive', desc: 'Tout compris' }
        ];

        const selected = step.prefilled || 'petit_dejeuner';

        return `
            <div class="wizard-step-content">
                <h2>${step.title}</h2>
                <p class="hint">Choisissez la formule de repas</p>
                
                <div class="meal-plan-options">
                    ${mealPlans.map(m => `
                        <label class="radio-card ${selected === m.value ? 'checked' : ''}">
                            <input 
                                type="radio" 
                                name="meal_plan" 
                                value="${m.value}"
                                ${selected === m.value ? 'checked' : ''}
                            />
                            <div class="radio-card-content">
                                <div class="radio-title">${m.label}</div>
                                <div class="radio-desc">${m.desc}</div>
                            </div>
                        </label>
                    `).join('')}
                </div>
            </div>
        `;
    }

    /**
     * Rendu de l'étape Prix
     */
    renderPricingStep(step) {
        const price = step.prefilled?.price || '';
        const isDayTrip = this.wizardData.is_day_trip;

        return `
            <div class="wizard-step-content">
                <h2>${step.title}</h2>
                <p class="hint">Indiquez le prix ${isDayTrip ? '' : 'par personne'}</p>
                
                <div class="form-group">
                    <label for="pack_price">Prix du voyage ${isDayTrip ? '' : '(par personne)'}</label>
                    <div class="price-input">
                        <input 
                            type="number" 
                            id="pack_price" 
                            class="form-control"
                            min="0"
                            step="10"
                            placeholder="0"
                            value="${price || ''}"
                        />
                        <span class="currency">€</span>
                    </div>
                </div>
                
                ${!isDayTrip ? `
                    <div class="form-group">
                        <label>Services inclus</label>
                        <div class="services-checkboxes">
                            <label class="checkbox-inline">
                                <input type="checkbox" id="service_guide" checked />
                                Guide francophone
                            </label>
                            <label class="checkbox-inline">
                                <input type="checkbox" id="service_entries" checked />
                                Entrées monuments
                            </label>
                            <label class="checkbox-inline">
                                <input type="checkbox" id="service_insurance" />
                                Assurance annulation
                            </label>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }

    /**
     * Rendu de l'étape Récapitulatif
     */
    renderSummaryStep() {
        const data = this.wizardData;

        return `
            <div class="wizard-step-content">
                <h2>✅ Récapitulatif de votre voyage</h2>
                <p class="hint">Vérifiez les informations avant de générer la fiche</p>
                
                <div class="summary-card">
                    <h3>📋 Informations générales</h3>
                    <ul class="summary-list">
                        ${!data.is_day_trip ? `<li><strong>Hôtel :</strong> ${data.hotel_name || 'Non spécifié'}</li>` : ''}
                        <li><strong>Destination :</strong> ${data.destination}</li>
                        <li><strong>Transport :</strong> ${this.getTransportLabel(data.transport_type)}</li>
                        ${data.transport_type === 'autocar' ? `
                            <li><strong>Point de départ :</strong> ${data.bus_departure_address || 'Non spécifié'}</li>
                            <li><strong>Durée trajet :</strong> ${data.travel_hours || 0}h ${data.travel_minutes || 0}min</li>
                        ` : ''}
                    </ul>
                </div>
                
                ${data.activities && data.activities.length > 0 ? `
                    <div class="summary-card">
                        <h3>🎯 Lieux d'intérêt</h3>
                        <ul class="activities-list">
                            ${data.activities.map(a => `<li>${this.escapeHtml(a)}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
                
                <div class="summary-card">
                    <h3>${data.is_day_trip ? '⏰ Horaires' : '📅 Dates et durée'}</h3>
                    <ul class="summary-list">
                        ${data.is_day_trip ? `
                            <li><strong>Départ :</strong> ${data.departure_time}</li>
                            <li><strong>Retour :</strong> ${data.return_time}</li>
                        ` : `
                            <li><strong>Du :</strong> ${data.date_start || 'À définir'}</li>
                            <li><strong>Au :</strong> ${data.date_end || 'À définir'}</li>
                            <li><strong>Nombre de personnes :</strong> ${data.num_people || 2}</li>
                            <li><strong>Catégorie :</strong> ${'⭐'.repeat(data.stars || 3)}</li>
                            <li><strong>Formule :</strong> ${this.getMealPlanLabel(data.meal_plan)}</li>
                        `}
                    </ul>
                </div>
                
                <div class="summary-card highlight">
                    <h3>💰 Prix</h3>
                    <p class="price-summary">${data.pack_price || 0} € ${!data.is_day_trip ? 'par personne' : ''}</p>
                </div>
                
                <div class="alert alert-info">
                    <p>✨ Prêt à générer votre fiche de voyage ?</p>
                    <p class="small">Les données seront enrichies avec des photos, vidéos et informations depuis nos APIs.</p>
                </div>
            </div>
        `;
    }

    /**
     * Initialise les événements spécifiques à chaque étape
     */
    initStepListeners(step) {
        switch (step.id) {
            case 'activities':
                this.initActivitiesListeners();
                break;
            case 'transport':
                this.initTransportListeners();
                break;
            case 'trip_type':
                this.initTripTypeListeners();
                break;
            case 'program':
                this.initProgramListeners();
                break;
            case 'dates':
                this.initDatesListeners();
                break;
        }
    }

    /**
     * Événements de l'étape Activités
     */
    initActivitiesListeners() {
        // Bouton ajouter
        const addBtn = document.getElementById('add-activity-btn');
        if (addBtn) {
            addBtn.addEventListener('click', () => this.addActivity());
        }

        // Boutons supprimer
        document.querySelectorAll('.delete-activity').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = e.target.dataset.index;
                this.removeActivity(index);
            });
        });
    }

    /**
     * Événements de l'étape Transport
     */
    initTransportListeners() {
        // Toggle champs autocar
        document.querySelectorAll('input[name="transport"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const autocarFields = document.getElementById('autocar-fields');
                const cards = document.querySelectorAll('.radio-card');
                
                cards.forEach(c => c.classList.remove('checked'));
                e.target.closest('.radio-card').classList.add('checked');
                
                if (autocarFields) {
                    autocarFields.style.display = (e.target.value === 'autocar') ? 'block' : 'none';
                }
            });
        });
    }

    /**
     * Événements de l'étape Type de séjour
     */
    initTripTypeListeners() {
        const dayTripCheckbox = document.getElementById('is_day_trip');
        const multiDayCheckbox = document.getElementById('is_multi_day');
        const dayTripFields = document.getElementById('day-trip-fields');

        if (dayTripCheckbox) {
            dayTripCheckbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    multiDayCheckbox.checked = false;
                    if (dayTripFields) dayTripFields.style.display = 'block';
                    document.querySelectorAll('.checkbox-card')[0].classList.add('checked');
                    document.querySelectorAll('.checkbox-card')[1].classList.remove('checked');
                } else {
                    multiDayCheckbox.checked = true;
                    if (dayTripFields) dayTripFields.style.display = 'none';
                    document.querySelectorAll('.checkbox-card')[0].classList.remove('checked');
                    document.querySelectorAll('.checkbox-card')[1].classList.add('checked');
                }
            });
        }

        if (multiDayCheckbox) {
            multiDayCheckbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    dayTripCheckbox.checked = false;
                    if (dayTripFields) dayTripFields.style.display = 'none';
                    document.querySelectorAll('.checkbox-card')[1].classList.add('checked');
                    document.querySelectorAll('.checkbox-card')[0].classList.remove('checked');
                } else {
                    dayTripCheckbox.checked = true;
                    if (dayTripFields) dayTripFields.style.display = 'block';
                    document.querySelectorAll('.checkbox-card')[1].classList.remove('checked');
                    document.querySelectorAll('.checkbox-card')[0].classList.add('checked');
                }
            });
        }
    }

    /**
     * Événements de l'étape Programme
     */
    initProgramListeners() {
        const generateBtn = document.getElementById('generate-program-btn');
        const regenerateBtn = document.getElementById('regenerate-program-btn');

        if (generateBtn) {
            generateBtn.addEventListener('click', () => this.generateProgram());
        }

        if (regenerateBtn) {
            regenerateBtn.addEventListener('click', () => this.generateProgram());
        }
    }

    /**
     * Événements de l'étape Dates
     */
    initDatesListeners() {
        // Boutons +/-
        document.querySelectorAll('.btn-number').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                const input = document.getElementById('num_people');
                let value = parseInt(input.value) || 2;

                if (action === 'plus') {
                    value++;
                } else if (action === 'minus' && value > 1) {
                    value--;
                }

                input.value = value;
            });
        });
    }

    /**
     * Ajoute une activité
     */
    addActivity() {
        const list = document.getElementById('activities-list');
        const index = list.children.length;

        const newActivity = document.createElement('div');
        newActivity.className = 'activity-item';
        newActivity.dataset.index = index;
        newActivity.innerHTML = `
            <span class="activity-drag-handle">⋮⋮</span>
            <input 
                type="text" 
                class="form-control activity-name" 
                placeholder="Nom du lieu"
            />
            <button type="button" class="btn-icon delete-activity" data-index="${index}">
                🗑️
            </button>
        `;

        list.appendChild(newActivity);

        // Attacher événement supprimer
        newActivity.querySelector('.delete-activity').addEventListener('click', (e) => {
            this.removeActivity(e.target.dataset.index);
        });

        // Focus sur le nouveau champ
        newActivity.querySelector('.activity-name').focus();
    }

    /**
     * Supprime une activité
     */
    removeActivity(index) {
        const item = document.querySelector(`.activity-item[data-index="${index}"]`);
        if (item) {
            item.remove();
        }
    }

    /**
     * Génère automatiquement un programme avec l'IA
     */
    async generateProgram() {
        this.showLoading('✨ Génération du programme avec l\'IA...');

        try {
            const response = await fetch('/api/ai-generate-program', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    destination: this.wizardData.destination,
                    activities: this.wizardData.activities,
                    departure_time: this.wizardData.departure_time || '08:00',
                    return_time: this.wizardData.return_time || '20:00',
                    departure_address: this.wizardData.bus_departure_address || 'Bruxelles'
                })
            });

            const data = await response.json();

            if (data.success) {
                this.wizardData.program = data.program;
                this.hideLoading();
                // Réafficher l'étape avec le programme
                this.showStep(this.currentStep);
            } else {
                throw new Error(data.error);
            }

        } catch (error) {
            console.error('❌ Erreur génération programme:', error);
            this.hideLoading();
            this.showError('Erreur lors de la génération du programme');
        }
    }

    /**
     * Sauvegarde les données de l'étape actuelle
     */
    saveCurrentStep() {
        const step = this.steps[this.currentStep];

        switch (step.id) {
            case 'hotel':
                this.wizardData.hotel_name = document.getElementById('hotel_name')?.value || '';
                break;

            case 'destination':
                this.wizardData.destination = document.getElementById('destination')?.value || '';
                break;

            case 'activities':
                this.wizardData.activities = Array.from(
                    document.querySelectorAll('.activity-name')
                ).map(input => input.value).filter(v => v.trim());
                break;

            case 'transport':
                this.wizardData.transport_type = document.querySelector('input[name="transport"]:checked')?.value;
                if (this.wizardData.transport_type === 'autocar') {
                    this.wizardData.bus_departure_address = document.getElementById('bus_departure_address')?.value || '';
                    this.wizardData.travel_hours = parseInt(document.getElementById('travel_hours')?.value || 0);
                    this.wizardData.travel_minutes = parseInt(document.getElementById('travel_minutes')?.value || 0);
                }
                break;

            case 'trip_type':
                this.wizardData.is_day_trip = document.getElementById('is_day_trip')?.checked || false;
                if (this.wizardData.is_day_trip) {
                    this.wizardData.departure_time = document.getElementById('departure_time')?.value || '08:00';
                    this.wizardData.return_time = document.getElementById('return_time')?.value || '20:00';
                }
                break;

            case 'schedule':
                this.wizardData.departure_time = document.getElementById('departure_time_confirm')?.value || '08:00';
                this.wizardData.return_time = document.getElementById('return_time_confirm')?.value || '20:00';
                break;

            case 'dates':
                this.wizardData.date_start = document.getElementById('date_start')?.value || '';
                this.wizardData.date_end = document.getElementById('date_end')?.value || '';
                this.wizardData.num_people = parseInt(document.getElementById('num_people')?.value || 2);
                break;

            case 'stars':
                this.wizardData.stars = parseInt(document.querySelector('input[name="stars"]:checked')?.value || 3);
                break;

            case 'meal_plan':
                this.wizardData.meal_plan = document.querySelector('input[name="meal_plan"]:checked')?.value || 'petit_dejeuner';
                break;

            case 'pricing':
                this.wizardData.pack_price = parseFloat(document.getElementById('pack_price')?.value || 0);
                if (!this.wizardData.is_day_trip) {
                    this.wizardData.services = {
                        guide: document.getElementById('service_guide')?.checked || false,
                        entries: document.getElementById('service_entries')?.checked || false,
                        insurance: document.getElementById('service_insurance')?.checked || false
                    };
                }
                break;
        }

        console.log('💾 Données sauvegardées:', this.wizardData);
    }

    /**
     * Passe à l'étape suivante
     */
    nextStep() {
        // Sauvegarder l'étape actuelle
        this.saveCurrentStep();

        // Validation basique
        if (!this.validateCurrentStep()) {
            return;
        }

        // Dernière étape : générer
        if (this.currentStep === this.totalSteps - 1) {
            this.generateTrip();
        } else {
            this.showStep(this.currentStep + 1);
        }
    }

    /**
     * Revient à l'étape précédente
     */
    prevStep() {
        if (this.currentStep > 0) {
            this.saveCurrentStep();
            this.showStep(this.currentStep - 1);
        }
    }

    /**
     * Passe l'étape actuelle
     */
    skipStep() {
        if (this.currentStep < this.totalSteps - 1) {
            this.showStep(this.currentStep + 1);
        }
    }

    /**
     * Valide l'étape actuelle
     */
    validateCurrentStep() {
        const step = this.steps[this.currentStep];

        switch (step.id) {
            case 'destination':
                const dest = document.getElementById('destination')?.value;
                if (!dest || !dest.trim()) {
                    this.showError('Veuillez indiquer une destination');
                    return false;
                }
                break;

            case 'pricing':
                const price = document.getElementById('pack_price')?.value;
                if (!price || parseFloat(price) <= 0) {
                    this.showError('Veuillez indiquer un prix valide');
                    return false;
                }
                break;
        }

        return true;
    }

    /**
     * Met à jour les boutons de navigation
     */
    updateNavigationButtons(stepIndex) {
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');
        const skipBtn = document.getElementById('skip-btn');

        if (prevBtn) {
            prevBtn.disabled = (stepIndex === 0);
        }

        if (nextBtn) {
            nextBtn.textContent = (stepIndex === this.totalSteps - 1) ? '🚀 Générer la fiche' : 'Suivant →';
        }

        if (skipBtn) {
            skipBtn.style.display = (stepIndex === this.totalSteps - 1) ? 'none' : 'inline-block';
        }
    }

    /**
     * Génère la fiche de voyage finale
     */
    async generateTrip() {
        this.showLoading('🚀 Génération de votre fiche de voyage...');

        try {
            const response = await fetch('/api/generate-preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    form_data: this.wizardData
                })
            });

            const result = await response.json();

            if (result.success) {
                this.hideLoading();
                this.showResults(result);
            } else {
                throw new Error(result.error);
            }

        } catch (error) {
            console.error('❌ Erreur génération:', error);
            this.hideLoading();
            this.showError('Erreur lors de la génération de la fiche');
        }
    }

    /**
     * Affiche les résultats de génération
     */
    showResults(result) {
        // TODO: Implémenter l'affichage des résultats
        // Pour l'instant, simple alert
        alert('✅ Fiche générée avec succès !\n\nMarge: ' + result.margin + '€\nÉconomies: ' + result.savings + '€');
        
        console.log('📊 Résultats:', result);
        
        // Proposer de sauvegarder
        if (confirm('Voulez-vous sauvegarder ce voyage ?')) {
            this.saveTrip(result);
        }
    }

    /**
     * Sauvegarde le voyage
     */
    async saveTrip(result) {
        try {
            const response = await fetch('/api/trips', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    form_data: this.wizardData,
                    api_data: result.api_data,
                    status: 'proposed'
                })
            });

            const data = await response.json();

            if (data.success) {
                alert('✅ Voyage sauvegardé avec succès !');
                window.location.href = '/agency/trips';
            } else {
                throw new Error(data.message);
            }

        } catch (error) {
            console.error('❌ Erreur sauvegarde:', error);
            alert('Erreur lors de la sauvegarde');
        }
    }

    /**
     * Affiche le container du wizard
     */
    showWizardContainer() {
        const step0 = document.getElementById('step-0');
        const wizardSteps = document.getElementById('wizard-steps');

        if (step0) step0.style.display = 'none';
        if (wizardSteps) wizardSteps.style.display = 'block';
    }

    /**
     * Affiche un loader
     */
    showLoading(message) {
        // Créer overlay si n'existe pas
        let overlay = document.getElementById('loading-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'loading-overlay';
            overlay.className = 'loading-overlay';
            overlay.innerHTML = `
                <div class="loading-spinner">
                    <div class="spinner"></div>
                    <p id="loading-message">${message}</p>
                </div>
            `;
            document.body.appendChild(overlay);
        }

        const messageEl = document.getElementById('loading-message');
        if (messageEl) messageEl.textContent = message;

        overlay.style.display = 'flex';
    }

    /**
     * Cache le loader
     */
    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }

    /**
     * Affiche une erreur
     */
    showError(message) {
        alert('❌ ' + message);
    }

    /**
     * Utilitaires
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    getTransportLabel(type) {
        const labels = {
            'avion': '✈️ Avion',
            'train': '🚂 Train',
            'autocar': '🚌 Autocar',
            'voiture': '🚗 Voiture'
        };
        return labels[type] || type;
    }

    getMealPlanLabel(plan) {
        const labels = {
            'logement_seul': '🔑 Logement seul',
            'petit_dejeuner': '☕ Petit-déjeuner',
            'demi_pension': '🍽️ Demi-pension',
            'pension_complete': '🍴 Pension complète',
            'all_in': '🎉 All Inclusive'
        };
        return labels[plan] || plan;
    }
}

// ============================================================================
// INITIALISATION GLOBALE
// ============================================================================

// Instance globale du wizard
let wizard = null;

// Initialiser au chargement de la page
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Initialisation du Wizard de Génération');
    wizard = new TravelWizard();
    wizard.init();
});
