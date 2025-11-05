// ============================================================================
// CSRF Helper
// ============================================================================

/**
 * Fonction globale pour effectuer des requêtes fetch avec le token CSRF.
 * @param {string} url - L'URL de l'API.
 * @param {object} options - Les options de la requête fetch.
 * @returns {Promise<Response>}
 */
async function fetchWithCSRF(url, options = {}) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    if (!options.headers) {
        options.headers = {};
    }
    if (csrfToken) {
        options.headers['X-CSRFToken'] = csrfToken;
    }
    return fetch(url, options);
}
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

        if (mode === 'ai') {
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelector(`[data-mode="ai"]`).classList.add('active');
            aiMode.style.display = 'block';
            manualMode.style.display = 'none';
        } else {
            this.switchToManualMode();
        }
    }

    /**
     * Passe en mode formulaire manuel complet
     */
    switchToManualMode() {
        console.log('Redirecting to manual form...');
        window.location.href = '/agency/generate/manual';
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
            const response = await fetchWithCSRF('/api/ai-parse-prompt', {
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
                hint: parsedData.hotel_name ? `✅ L'IA a détecté : ${parsedData.hotel_name}` : 
                      (parsedData.destination ? `Hôtel à ${parsedData.destination}` : '')
            });
        }

        // Étape 2 : Destination
        steps.push({
            id: 'destination',
            title: '📍 Confirmez la destination',
            prefilled: parsedData.destination || '',
            hint: parsedData.destination ? '✅ Détecté automatiquement par l\'IA' : ''
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
                { id: 'schedule', title: '🗓️ Date & Horaires', prefilled: {} },
                { id: 'program', title: '📋 Programme de la journée', prefilled: [] },
                { id: 'pricing_day_trip', title: '💰 Prix', prefilled: { price: parsedData.price || null } },
                { id: 'options', title: '✨ Options Finales', prefilled: {} }
            );
        } else {
            // Séjour normal
            steps.push(
                { 
                    id: 'dates', 
                    title: '🗓️ Dates du séjour', 
                    prefilled: { 
                        duration: parsedData.estimated_duration || 3,
                        date_start: parsedData.date_start || '',
                        date_end: parsedData.date_end || ''
                    } 
                },
                { id: 'stars', title: '⭐ Catégorie de l\'hôtel', prefilled: parsedData.stars || 3 },
                { id: 'meal_plan', title: '🍽️ Formule repas', prefilled: parsedData.meal_plan || 'petit_dejeuner' },
                { id: 'pricing_stay', title: '💰 Tarification & Marges', prefilled: { price: parsedData.price || null } },
                { id: 'options', title: '✨ Options Finales', prefilled: {} }
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
            case 'pricing_day_trip':
                return this.renderPricingDayTripStep(step);
            case 'pricing_stay':
                return this.renderPricingStayStep(step);
            case 'options':
                return this.renderOptionsStep(step);
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
                    <!-- NOUVEAU : Container pour les résultats d'autocomplétion -->
                    <div id="hotel-autocomplete-results" class="autocomplete-results"></div>
                    <input type="hidden" id="hotel_place_id">
                    <input type="hidden" id="hotel_address">
                    <input type="hidden" id="hotel_lat">
                    <input type="hidden" id="hotel_lng">
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
        <p class="hint">Choisissez le moyen de transport principal et renseignez les coûts associés.</p>
        
        <div class="transport-options">
            ${transports.map(t => `
                <label class="radio-card ${selected === t.value ? 'checked' : ''}">
                    <input type="radio" name="transport" value="${t.value}" ${selected === t.value ? 'checked' : ''} />
                    <span class="radio-card-content">
                        <span class="radio-icon">${t.icon}</span>
                        <span class="radio-label">${t.label.replace(t.icon + ' ', '')}</span>
                    </span>
                </label>
            `).join('')}
        </div>
        
        <div id="transport-details-container" class="mt-4 space-y-4">
            <!-- Champs pour Autocar -->
            <div id="autocar-fields" class="hidden">
                <div class="form-group"><label for="bus_departure_address">Point de départ de l'autocar</label><input type="text" id="bus_departure_address" class="form-control" placeholder="Ex: Place de la Gare, Bruxelles" value="${this.wizardData.bus_departure_address || ''}"></div>
            </div>

            <!-- Champs pour Train -->
            <div id="train-fields" class="hidden">
                <div class="form-row"><div class="form-group"><label for="departure_station">Gare de départ</label><input type="text" id="departure_station" class="form-control" placeholder="Saisir une gare..."></div><div class="form-group"><label for="arrival_station">Gare d'arrivée</label><input type="text" id="arrival_station" class="form-control" placeholder="Saisir une gare..."></div></div>
                <div class="form-group"><label for="train_price">Prix du trajet (€)</label><input type="number" id="train_price" class="form-control cost-input" value="${this.wizardData.train_price || 0}"></div>
            </div>

            <!-- Champs pour Avion -->
            <div id="avion-fields" class="hidden">
                <div class="form-row"><div class="form-group"><label for="departure_airport">Aéroport de départ</label><input type="text" id="departure_airport" class="form-control" placeholder="Saisir un aéroport..."></div><div class="form-group"><label for="arrival_airport">Aéroport d'arrivée</label><input type="text" id="arrival_airport" class="form-control" placeholder="Saisir un aéroport..."></div></div>
                <div class="form-row"><div class="form-group"><label for="baggage_type">🧳 Bagages</label><select id="baggage_type" class="form-control"><option>Pas de bagages</option><option selected>Bagage cabine (10kg)</option><option>Bagage cabine + 1x 23kg en soute</option></select></div><div class="form-group"><label for="flight_price">Prix du vol (€)</label><input type="number" id="flight_price" class="form-control cost-input" value="${this.wizardData.flight_price || 0}"></div></div>
            </div>

            <!-- Coûts additionnels (pour séjours) -->
            ${!this.wizardData.is_day_trip ? `
            <div class="form-row">
                <div class="form-group"><label for="transfer_cost">🚐 Coût des Transferts (€)</label><input type="number" id="transfer_cost" class="form-control cost-input" value="${this.wizardData.transfer_cost || 0}"></div>
                <div class="form-group"><label for="car_rental_cost">🚗 Voiture de location (€)</label><input type="number" id="car_rental_cost" class="form-control cost-input" value="${this.wizardData.car_rental_cost || 0}"></div>
            </div>
            ` : ''}
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
                
                <div class="form-group">
                    <label for="day_trip_date">Date de l'excursion</label>
                    <input type="text" id="day_trip_date" class="form-control" readonly placeholder="Cliquez pour choisir une date" value="${this.wizardData.date_start || ''}">
                </div>

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
                    <div class="alert alert-info text-center">
                        <p>Souhaitez-vous générer automatiquement un programme avec l'IA ?</p>
                        <button type="button" id="generate-program-btn" class="btn btn-primary mt-2">
                            ✨ Générer le programme automatiquement
                        </button>
                    </div>
                ` : ''}
                
                <!-- MODIFIÉ : Amélioration de l'affichage de la timeline -->
                <div id="program-timeline" class="program-timeline">
                    ${program.map((item) => `
                        <div class="timeline-item">
                            <input type="time" class="timeline-time" value="${item.time}">
                            <div class="timeline-line"></div>
                            <input type="text" class="timeline-activity form-control" value="${this.escapeHtml(item.activity)}">
                            <button type="button" class="btn-icon delete-timeline-item">🗑️</button>
                        </div>
                    `).join('')}
                </div>
                
                ${program.length > 0 ? `
                    <button type="button" id="regenerate-program-btn" class="btn btn-secondary mt-3">
                        🔄 Régénérer le programme
                    </button>
                    <button type="button" id="add-timeline-item-btn" class="btn btn-secondary mt-3 ml-2">
                        ➕ Ajouter une étape
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
        const dateStart = step.prefilled?.date_start || this.wizardData.date_start || '';
        const dateEnd = step.prefilled?.date_end || this.wizardData.date_end || '';
        const hasPrefilledDates = dateStart && dateEnd;

        return `
            <div class="wizard-step-content">
                <h2>${step.title}</h2>
                <p class="hint">${hasPrefilledDates ? '✅ Dates détectées automatiquement - vous pouvez les modifier' : 'Quand souhaitez-vous partir ?'}</p>
                
                <div class="row">
                    <div class="col-md-6">
                        <div class="form-group">
                            <label for="date_start">Date de départ</label>
                            <input 
                                type="date" 
                                id="date_start" 
                                class="form-control"
                                min="${today}"
                                value="${dateStart}"
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
                                value="${dateEnd}"
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
    renderPricingDayTripStep(step) {
        const price = step.prefilled?.price || '';
        return `
    <div class="wizard-step-content">
        <h2>${step.title}</h2>
        <p class="hint">Indiquez le prix final de l'excursion.</p>
        <div class="form-group">
            <label for="pack_price">Prix du pack (€)</label>
            <div class="price-input">
                <input type="number" id="pack_price" class="form-control cost-input" min="0" step="10" placeholder="0" value="${price || ''}" />
                <span class="currency">€</span>
            </div>
        </div>
    </div>
`;
    }

    renderPricingStayStep(step) {
        const price = step.prefilled?.price || '';
        return `
    <div class="wizard-step-content">
        <h2>${step.title}</h2>
        <p class="hint">Renseignez les coûts pour calculer vos marges.</p>
        
        <div class="form-row">
            <div class="form-group"><label for="hotel_b2b_price">Tarif Hôtel B2B (€)</label><input type="number" id="hotel_b2b_price" class="form-control cost-input" placeholder="ex: 2000" value="${this.wizardData.hotel_b2b_price || ''}"></div>
            <div class="form-group"><label for="hotel_b2c_price">Tarif Hôtel B2C (€)</label><input type="number" id="hotel_b2c_price" class="form-control cost-input" placeholder="ex: 2800" value="${this.wizardData.hotel_b2c_price || ''}"></div>
        </div>
        <div class="form-row">
            <div class="form-group"><label for="surcharge_cost">Surcoût Pension (€)</label><input type="number" id="surcharge_cost" class="form-control cost-input" value="${this.wizardData.surcharge_cost || 0}"></div>
        </div>

        <h3 class="section-divider"><span>Prix Final</span></h3>
        <div class="form-group">
            <label for="pack_price">Prix du pack (€) *</label>
            <div class="price-input">
                <input type="number" id="pack_price" required class="form-control cost-input" placeholder="ex: 2400" value="${price || ''}">
                <span class="currency">€</span>
            </div>
        </div>

        <div class="cost-calculator">
            <div><p>Coût B2B</p><span id="total-b2b-cost" class="cost-value">0 €</span></div>
            <div><p>Coût B2C</p><span id="total-b2c-cost" class="cost-value">0 €</span></div>
            <div><p>Écart B2C/B2B</p><span id="b2c-b2b-gap" class="cost-value">0 €</span></div>
            <div><p>Économie Client</p><span id="client-saving" class="cost-value" style="color: #10b981;">0 €</span></div>
            <div><p>Marge Finale</p><span id="final-margin" class="cost-value" style="color: #2563eb;">0 €</span></div>
            <div><p>Marge Vendeur</p><span id="seller-margin" class="cost-value" style="color: #2563eb;">0 €</span></div>
            <div><p>Marge Agence</p><span id="vp-margin" class="cost-value" style="color: #2563eb;">0 €</span></div>
        </div>
    </div>
`;
    }

    renderOptionsStep(step) {
        return `
    <div class="wizard-step-content">
        <h2>${step.title}</h2>
        <p class="hint">Ajoutez des services ou des conditions particulières.</p>

        <div class="form-group">
            <label for="exclusive_services">Services Exclusifs Inclus</label>
            <textarea id="exclusive_services" class="form-control" rows="3" placeholder="ex: Accès au lounge VIP de l'aéroport&#10;Une bouteille de champagne en chambre...">${this.wizardData.exclusive_services || ''}</textarea>
        </div>

        <div class="form-group">
            <div class="flex items-center gap-4">
                <div class="flex items-center">
                    <input type="checkbox" id="has_cancellation" class="h-4 w-4 mr-2" ${this.wizardData.has_cancellation ? 'checked' : ''}>
                    <label for="has_cancellation" class="mb-0">Annulation gratuite</label>
                </div>
                <div id="cancellation_date_wrapper" class="${this.wizardData.has_cancellation ? '' : 'hidden'} flex-grow">
                    <input type="text" id="cancellation_date" class="form-control" readonly placeholder="Jusqu'au..." value="${this.wizardData.cancellation_date || ''}">
                </div>
            </div>
        </div>

        <div class="form-group bg-red-50 border border-red-200 p-3 rounded-lg">
            <label for="is_ultra_budget" class="flex items-center gap-3 m-0 text-red-700 font-semibold">
                <input type="checkbox" id="is_ultra_budget" value="true" class="h-5 w-5" ${this.wizardData.is_ultra_budget ? 'checked' : ''}>
                ⚠️ Marquer comme "Ultra Budget"
            </label>
        </div>
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
                        <ul class="summary-list">
                            ${data.activities.map(a => `<li>${this.escapeHtml(a)}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
                
                <div class="summary-card">
                    <h3>${data.is_day_trip ? '⏰ Horaires' : '📅 Dates et durée'}</h3>
                    <ul class="summary-list">
                        ${data.is_day_trip ? `
                            <li><strong>Date :</strong> ${data.date_start ? new Date(data.date_start).toLocaleDateString('fr-FR') : 'À définir'}</li>
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
                
                ${data.exclusive_services || data.has_cancellation ? `
                <div class="summary-card">
                    <h3>✨ Options</h3>
                    <ul class="summary-list">
                        ${data.exclusive_services ? `<li><strong>Services exclusifs :</strong><br><pre>${this.escapeHtml(data.exclusive_services)}</pre></li>` : ''}
                        ${data.has_cancellation ? `<li><strong>Annulation gratuite :</strong> Jusqu'au ${data.cancellation_date || 'N/A'}</li>` : ''}
                    </ul>
                </div>
                ` : ''}

                <div class="summary-card highlight">
                    <h3>💰 Prix</h3>
                    <p class="price-summary">${data.pack_price || 0} € ${!data.is_day_trip ? 'par personne' : ''}</p>
                    ${!data.is_day_trip ? `<p class="text-sm">Marge finale estimée : ${data.final_margin || 0} €</p>` : ''}
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
            // MODIFIÉ : Ajouter l'initialisation pour l'étape hôtel
            case 'hotel':
                this.initHotelAutocomplete();
                break;
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
            case 'schedule':
                this.initScheduleListeners();
                break;
            case 'dates':
                this.initDatesListeners();
                break;
            case 'stars':
                this.initStarsListeners();
                break;
            case 'pricing_stay':
                this.initPricingStayListeners();
                break;
            case 'options':
                this.initOptionsListeners();
                break;
        }
    }

    /**
     * NOUVEAU : Initialise l'autocomplétion pour le champ hôtel
     */
    initHotelAutocomplete() {
        const input = document.getElementById('hotel_name');
        const resultsContainer = document.getElementById('hotel-autocomplete-results');
        let debounceTimer;

        if (!input || !resultsContainer) return;

        // Si le champ est pré-rempli, déclencher automatiquement l'autocomplétion
        if (input.value && input.value.length >= 3) {
            setTimeout(() => {
                this.triggerHotelAutocomplete(input.value);
            }, 500);
        }

        input.addEventListener('keyup', (e) => {
            clearTimeout(debounceTimer);
            const query = e.target.value;

            if (query.length < 3) {
                resultsContainer.innerHTML = '';
                resultsContainer.style.display = 'none';
                return;
            }

            debounceTimer = setTimeout(() => {
                this.triggerHotelAutocomplete(query);
            }, 300);
        });

        // Gérer la sélection d'un résultat
        resultsContainer.addEventListener('click', (e) => {
            const item = e.target.closest('.autocomplete-item');
            if (item) {
                const placeId = item.dataset.placeId;
                const description = item.dataset.description;
                input.value = description;
                document.getElementById('hotel_place_id').value = placeId;
                resultsContainer.innerHTML = '';
                resultsContainer.style.display = 'none';
                this.getPlaceDetails(placeId);
            }
        });

        // Cacher les résultats si on clique ailleurs
        document.addEventListener('click', (e) => {
            if (!input.contains(e.target) && !resultsContainer.contains(e.target)) {
                resultsContainer.style.display = 'none';
            }
        });
    }

    /**
     * NOUVEAU : Déclenche l'autocomplétion et sélectionne automatiquement le premier résultat
     */
    async triggerHotelAutocomplete(query) {
        const resultsContainer = document.getElementById('hotel-autocomplete-results');
        const input = document.getElementById('hotel_name');
        
        if (!resultsContainer || !input) return;

        try {
            const response = await fetchWithCSRF('/api/google/autocomplete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ input: query })
            });
            const data = await response.json();

            if (data.success && data.predictions.length > 0) {
                resultsContainer.innerHTML = data.predictions.map(p => `
                    <div class="autocomplete-item" data-place-id="${p.place_id}" data-description="${this.escapeHtml(p.description)}">
                        <strong>${this.escapeHtml(p.structured_formatting.main_text)}</strong>
                        <small>${this.escapeHtml(p.structured_formatting.secondary_text)}</small>
                    </div>
                `).join('');
                resultsContainer.style.display = 'block';

                // Si c'est une autocomplétion automatique (pré-remplissage), sélectionner le premier résultat
                const firstPrediction = data.predictions[0];
                const prefilledValue = this.steps[this.currentStep]?.prefilled || '';
                
                // Vérifier si le champ contient exactement la valeur pré-remplie (pas de modification utilisateur)
                if (prefilledValue && input.value === prefilledValue) {
                    // Sélectionner automatiquement le premier résultat après un court délai
                    setTimeout(() => {
                        input.value = firstPrediction.description;
                        document.getElementById('hotel_place_id').value = firstPrediction.place_id;
                        resultsContainer.innerHTML = '';
                        resultsContainer.style.display = 'none';
                        this.getPlaceDetails(firstPrediction.place_id);
                        
                        // Afficher un indicateur visuel
                        input.style.borderColor = '#10b981';
                        input.style.borderWidth = '2px';
                        setTimeout(() => {
                            input.style.borderColor = '';
                            input.style.borderWidth = '';
                        }, 2000);
                    }, 800);
                }
            } else {
                resultsContainer.innerHTML = '';
                resultsContainer.style.display = 'none';
            }
        } catch (error) {
            console.error('Erreur autocomplétion:', error);
        }
    }

    /**
     * NOUVEAU : Récupère les détails d'un lieu (lat, lng, adresse)
     */
    async getPlaceDetails(placeId) {
        try {
            const response = await fetchWithCSRF('/api/google/place-details', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ place_id: placeId })
            });
            const data = await response.json();
            if (data.success && data.result) {
                document.getElementById('hotel_address').value = data.result.formatted_address || '';
                document.getElementById('hotel_lat').value = data.result.geometry.location.lat || '';
                document.getElementById('hotel_lng').value = data.result.geometry.location.lng || '';
                console.log('📍 Détails du lieu récupérés:', data.result);
            }
        } catch (error) {
            console.error('Erreur place details:', error);
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
        // Autocomplétion
        initAutocomplete('departure_airport', null, 'airport');
        initAutocomplete('arrival_airport', null, 'airport');
        initAutocomplete('departure_station', null, 'train_station');
        initAutocomplete('arrival_station', null, 'train_station');

        // Mettre à jour les champs affichés
        this.toggleTransportFields();

        // Toggle champs autocar
        document.querySelectorAll('input[name="transport"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const autocarFields = document.getElementById('autocar-fields');
                const cards = document.querySelectorAll('.radio-card');
                
                cards.forEach(c => c.classList.remove('checked'));
                e.target.closest('.radio-card').classList.add('checked');
                
                this.toggleTransportFields();
            });
        });
    }

    toggleTransportFields() {
        const transportType = document.querySelector('input[name="transport"]:checked')?.value;
        const fields = {
            'autocar': document.getElementById('autocar-fields'),
            'train': document.getElementById('train-fields'),
            'avion': document.getElementById('avion-fields')
        };

        for (const type in fields) {
            if (fields[type]) {
                fields[type].classList.toggle('hidden', type !== transportType);
            }
        }
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
     * Événements de l'étape Type de séjour
     */
    initScheduleListeners() {
        new Litepicker({
            element: document.getElementById('day_trip_date'),
            singleMode: true,
            lang: 'fr-FR',
            format: 'DD MMMM YYYY'
        });
    }

    initProgramListeners() {
        const generateBtn = document.getElementById('generate-program-btn');
        const regenerateBtn = document.getElementById('regenerate-program-btn');

        if (generateBtn) {
            generateBtn.addEventListener('click', () => this.generateProgram());
        }

        if (regenerateBtn) {
            regenerateBtn.addEventListener('click', () => this.generateProgram());
        }

        // MODIFIÉ : Ajouter la logique pour les nouveaux boutons
        const addBtn = document.getElementById('add-timeline-item-btn');
        if (addBtn) {
            addBtn.addEventListener('click', () => this.addTimelineItem());
        }

        document.querySelectorAll('.delete-timeline-item').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.target.closest('.timeline-item').remove();
            });
        });
    }

    /**
     * NOUVEAU : Ajoute une nouvelle ligne vide à la timeline du programme
     */
    addTimelineItem() {
        const timeline = document.getElementById('program-timeline');
        if (!timeline) return;

        const newItem = document.createElement('div');
        newItem.className = 'timeline-item';
        newItem.innerHTML = `
            <input type="time" class="timeline-time" value="12:00">
            <div class="timeline-line"></div>
            <input type="text" class="timeline-activity form-control" placeholder="Nouvelle activité...">
            <button type="button" class="btn-icon delete-timeline-item">🗑️</button>
        `;
        timeline.appendChild(newItem);

        newItem.querySelector('.delete-timeline-item').addEventListener('click', (e) => {
            e.target.closest('.timeline-item').remove();
        });
    }

    /**
     * Événements de l'étape Catégorie (Étoiles)
     */
    initStarsListeners() {
        document.querySelectorAll('.star-option').forEach(option => {
            option.addEventListener('click', (e) => {
                const selectedOption = e.currentTarget;
                // Retirer la classe 'selected' de tous les autres
                document.querySelectorAll('.star-option').forEach(opt => {
                    opt.classList.remove('selected');
                });
                // Ajouter la classe à l'élément cliqué
                selectedOption.classList.add('selected');
            });
        });
    }

    initPricingStayListeners() {
        this.updateCostTotals(); // Initial calculation
        document.querySelectorAll('.cost-input').forEach(input => {
            input.addEventListener('input', () => this.updateCostTotals());
        });
    }

    updateCostTotals() {
        const getVal = (id) => parseFloat(document.getElementById(id)?.value) || 0;
        const hotelB2B = getVal('hotel_b2b_price');
        const hotelB2C = getVal('hotel_b2c_price');
        const flight = getVal('flight_price');
        const train = getVal('train_price');
        const transfer = getVal('transfer_cost');
        const car = getVal('car_rental_cost');
        const surcharge = getVal('surcharge_cost');
        const packPrice = getVal('pack_price');

        const totalB2B = hotelB2B + flight + train + transfer + car + surcharge;
        const totalB2C = hotelB2C + flight + train + transfer + car + surcharge;
        const gap = totalB2C - totalB2B;
        const saving = totalB2C - packPrice;
        const finalMargin = packPrice - totalB2B;
        const sellerMargin = Math.round(finalMargin * (window.userMarginPercentage / 100));
        const vpMargin = finalMargin - sellerMargin;

        document.getElementById('total-b2b-cost').textContent = `${totalB2B.toFixed(0)} €`;
        document.getElementById('total-b2c-cost').textContent = `${totalB2C.toFixed(0)} €`;
        document.getElementById('b2c-b2b-gap').textContent = `${gap.toFixed(0)} €`;
        document.getElementById('client-saving').textContent = `${saving.toFixed(0)} €`;
        document.getElementById('final-margin').textContent = `${finalMargin.toFixed(0)} €`;
        document.getElementById('seller-margin').textContent = `${sellerMargin.toFixed(0)} €`;
        document.getElementById('vp-margin').textContent = `${vpMargin.toFixed(0)} €`;

        // Sauvegarder les marges pour le récap
        this.wizardData.final_margin = finalMargin;
    }

    initOptionsListeners() {
        document.getElementById('has_cancellation').addEventListener('change', (e) => {
            document.getElementById('cancellation_date_wrapper').classList.toggle('hidden', !e.target.checked);
        });
        new Litepicker({ element: document.getElementById('cancellation_date'), singleMode: true, lang: 'fr-FR', format: 'DD MMMM YYYY' });
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
            const response = await fetchWithCSRF('/api/ai-generate-program', {
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
                this.wizardData.hotel_place_id = document.getElementById('hotel_place_id')?.value || '';
                this.wizardData.hotel_address = document.getElementById('hotel_address')?.value || '';
                this.wizardData.hotel_lat = document.getElementById('hotel_lat')?.value || '';
                this.wizardData.hotel_lng = document.getElementById('hotel_lng')?.value || '';
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
                this.wizardData.bus_departure_address = document.getElementById('bus_departure_address')?.value || '';
                this.wizardData.departure_station = document.getElementById('departure_station')?.value || '';
                this.wizardData.arrival_station = document.getElementById('arrival_station')?.value || '';
                this.wizardData.train_price = parseFloat(document.getElementById('train_price')?.value || 0);
                this.wizardData.departure_airport = document.getElementById('departure_airport')?.value || '';
                this.wizardData.arrival_airport = document.getElementById('arrival_airport')?.value || '';
                this.wizardData.baggage_type = document.getElementById('baggage_type')?.value || '';
                this.wizardData.flight_price = parseFloat(document.getElementById('flight_price')?.value || 0);
                if (!this.wizardData.is_day_trip) {
                    this.wizardData.transfer_cost = parseFloat(document.getElementById('transfer_cost')?.value || 0);
                    this.wizardData.car_rental_cost = parseFloat(document.getElementById('car_rental_cost')?.value || 0);
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
                this.wizardData.date_start = document.getElementById('day_trip_date')?.value || '';
                this.wizardData.departure_time = document.getElementById('departure_time_confirm')?.value || '08:00';
                this.wizardData.return_time = document.getElementById('return_time_confirm')?.value || '20:00';
                break;

            // MODIFIÉ : Sauvegarder le programme depuis les champs de la timeline
            case 'program':
                this.wizardData.program = Array.from(document.querySelectorAll('.timeline-item')).map(item => {
                    return {
                        time: item.querySelector('.timeline-time').value,
                        activity: item.querySelector('.timeline-activity').value
                    };
                }).filter(item => item.activity); // Ne pas sauvegarder les lignes vides
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

            case 'pricing_day_trip':
                this.wizardData.pack_price = parseFloat(document.getElementById('pack_price')?.value || 0);
                break;

            case 'pricing_stay':
                this.wizardData.hotel_b2b_price = parseFloat(document.getElementById('hotel_b2b_price')?.value || 0);
                this.wizardData.hotel_b2c_price = parseFloat(document.getElementById('hotel_b2c_price')?.value || 0);
                this.wizardData.surcharge_cost = parseFloat(document.getElementById('surcharge_cost')?.value || 0);
                this.wizardData.pack_price = parseFloat(document.getElementById('pack_price')?.value || 0);
                break;

            case 'options':
                this.wizardData.exclusive_services = document.getElementById('exclusive_services')?.value || '';
                this.wizardData.has_cancellation = document.getElementById('has_cancellation')?.checked || false;
                this.wizardData.cancellation_date = document.getElementById('cancellation_date')?.value || '';
                this.wizardData.is_ultra_budget = document.getElementById('is_ultra_budget')?.checked || false;
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

            case 'pricing_day_trip':
            case 'pricing_stay':
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
     * Génère la fiche de voyage finale - Redirige vers le formulaire manuel pré-rempli
     */
    async generateTrip() {
        this.showLoading('✨ Préparation du formulaire...');

        try {
            // Sauvegarder les données du wizard dans sessionStorage pour les transférer au formulaire manuel
            sessionStorage.setItem('wizardData', JSON.stringify(this.wizardData));
            
            this.hideLoading();
            
            // Rediriger vers le formulaire manuel qui sera pré-rempli
            window.location.href = '/agency/generate/manual?from_wizard=true';

        } catch (error) {
            console.error('❌ Erreur:', error);
            this.hideLoading();
            this.showError(`Erreur lors de la préparation: ${error.message}`);
        }
    }

    /**
     * Affiche les résultats de génération et propose de sauvegarder
     */
    showResults(resultData, htmlPreview) {
        // MODIFIÉ : Afficher un modal avec un iframe pour l'aperçu
        console.log('📊 Résultats de la génération:', resultData);

        let modal = document.getElementById('preview-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'preview-modal';
            modal.className = 'preview-modal';
            document.body.appendChild(modal);
        }

        modal.innerHTML = `
            <div class="preview-modal-content">
                <div class="preview-modal-header">
                    <h2>Aperçu de la Fiche de Voyage</h2>
                    <button id="close-preview-btn" class="close-btn">&times;</button>
                </div>
                <div class="preview-modal-body">
                    <iframe id="preview-iframe" src="about:blank"></iframe>
                </div>
                <div class="preview-modal-footer">
                    <button id="edit-trip-btn" class="btn btn-secondary">Modifier</button>
                    <button id="save-trip-btn" class="btn btn-primary">💾 Enregistrer comme proposition</button>
                </div>
            </div>
        `;

        modal.style.display = 'flex';

        const iframe = document.getElementById('preview-iframe');
        iframe.contentWindow.document.open();
        iframe.contentWindow.document.write(htmlPreview);
        iframe.contentWindow.document.close();

        document.getElementById('close-preview-btn').onclick = () => modal.style.display = 'none';
        document.getElementById('edit-trip-btn').onclick = () => modal.style.display = 'none'; // L'utilisateur peut alors modifier le wizard
        document.getElementById('save-trip-btn').onclick = () => {
            modal.style.display = 'none';
            this.saveTrip(resultData);
        };
    }
    
    /**
     * Sauvegarde le voyage en appelant l'API backend
     */
    async saveTrip(result) {
        this.showLoading('💾 Enregistrement du voyage...');

        try {
            const response = await fetchWithCSRF('/api/trips', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                // MODIFIÉ : Le corps de la requête contient maintenant toutes les données
                body: JSON.stringify({
                    form_data: result.form_data,
                    api_data: result.api_data,
                    status: 'proposed' // Statut initial
                })
            });

            const data = await response.json();
            this.hideLoading();

            if (data.success) {
                showToast('Voyage sauvegardé avec succès !');
                window.location.href = '/agency/trips'; // Rediriger l'utilisateur
            } else {
                throw new Error(data.message || 'Une erreur est survenue lors de la sauvegarde.');
            }

        } catch (error) {
            console.error('Erreur sauvegarde:', error);
            this.hideLoading();
            this.showError(`Erreur lors de la sauvegarde: ${error.message}`);
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
        // Utilise la fonction globale showToast
        showToast(message, 'error');
    }

    /**
     * Utilitaires
     */
    escapeHtml(text) {
        if (text === null || text === undefined) {
            return '';
        }
        const div = document.createElement('div');
        div.textContent = text.toString();
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
