# services/ai_assistant.py
"""
Assistant IA pour le parsing de prompts et génération de contenu
Utilise Google Gemini API pour analyser les demandes en langage naturel
"""

import google.generativeai as genai
import json
from typing import Dict, Any, List, Optional
import re


class AIAssistant:
    """Gestionnaire d'intelligence artificielle pour l'assistance voyage"""
    
    def __init__(self, api_key: str):
        """
        Initialise l'assistant IA avec une clé API Gemini
        
        Args:
            api_key: Clé API Google Gemini de l'agence
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    def parse_travel_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Parse un prompt en langage naturel et extrait les informations de voyage
        
        Args:
            prompt: Description en langage naturel du voyage
                    Ex: "Voyage en autocar à Rome, Colisée + Vatican, 100€"
        
        Returns:
            Dict contenant les informations structurées :
            {
                "destination": "Rome, Italie",
                "transport_type": "autocar",
                "is_day_trip": false,
                "activities": ["Colisée", "Vatican"],
                "price": 100,
                "hotel_name": null,
                "estimated_duration": 3,
                "stars": 3,
                "meal_plan": "petit_dejeuner",
                "num_people": 2,
                "departure_city": null
            }
        """
        
        system_prompt = """
Tu es un assistant spécialisé dans l'analyse de demandes de voyages.
À partir d'une description en langage naturel, extrais et structure les informations.

CHAMPS À EXTRAIRE :

OBLIGATOIRES :
- destination (string) : ville, pays (format "Ville, Pays")
- transport_type (string) : "avion" | "train" | "autocar" | "voiture"
- is_day_trip (boolean) : true si "excursion" ou "journée" ou "day trip" ou "1 jour" ou "une journée"

OPTIONNELS :
- hotel_name (string|null) : nom de l'hôtel si mentionné explicitement
- activities (array) : liste des lieux/visites mentionnés
- price (number|null) : prix par personne si mentionné (extraire juste le nombre)
- estimated_duration (number|null) : nombre de jours/nuits (0 si voyage d'un jour)
- departure_city (string|null) : ville de départ si mentionnée
- num_people (number|null) : nombre de personnes si mentionné (défaut: 2)
- stars (number|null) : catégorie hôtel (1-5) selon le budget
- meal_plan (string|null) : "logement_seul" | "petit_dejeuner" | "demi_pension" | "pension_complete" | "all_in"

RÈGLES D'INTELLIGENCE :

1. Budget & Catégorie :
   - Si budget < 300€ → stars: 2-3, meal_plan: "logement_seul" ou "petit_dejeuner"
   - Si budget 300-600€ → stars: 3-4, meal_plan: "demi_pension"
   - Si budget > 600€ → stars: 4-5, meal_plan: "pension_complete" ou "all_in"

2. Transport & Distance :
   - Si "autocar" → destination Europe max (< 2000km de Bruxelles)
   - Si "avion" → destinations internationales possibles
   - Si "train" → destinations européennes accessibles par rail

3. Durée :
   - Si "excursion" ou "journée" ou "1 jour" → is_day_trip: true, estimated_duration: 0
   - Si mention "3 jours" → estimated_duration: 3
   - Si mention "week-end" → estimated_duration: 2
   - Si mention "semaine" → estimated_duration: 7
   - Si pas de mention et pas d'excursion → estimated_duration: 3 (par défaut)

4. Activités :
   - Extraire TOUS les lieux/monuments/activités mentionnés
   - Si destination connue sans activité mentionnée, suggérer 2-3 attractions principales
   - Exemples : Paris → ["Tour Eiffel", "Louvre", "Montmartre"]

5. Hôtel :
   - Ne remplir hotel_name QUE si un nom d'hôtel est explicitement mentionné
   - Ne PAS inventer de nom d'hôtel

EXEMPLES :

Input: "Voyage en autocar à Rome, excursion Colisée + Vatican, 100€"
Output: {
    "destination": "Rome, Italie",
    "transport_type": "autocar",
    "is_day_trip": false,
    "activities": ["Colisée", "Vatican"],
    "price": 100,
    "hotel_name": null,
    "estimated_duration": 3,
    "stars": 3,
    "meal_plan": "petit_dejeuner",
    "num_people": 2,
    "departure_city": null
}

Input: "Excursion d'une journée à Bruges en autocar, 50€"
Output: {
    "destination": "Bruges, Belgique",
    "transport_type": "autocar",
    "is_day_trip": true,
    "activities": ["Grand-Place de Bruges", "Béguinage", "Canaux"],
    "price": 50,
    "hotel_name": null,
    "estimated_duration": 0,
    "num_people": 2,
    "departure_city": null,
    "stars": null,
    "meal_plan": null
}

Input: "Week-end romantique à Paris, train TGV depuis Bruxelles, hôtel 4 étoiles Le Marais, 350€"
Output: {
    "destination": "Paris, France",
    "transport_type": "train",
    "is_day_trip": false,
    "activities": ["Tour Eiffel", "Louvre", "Montmartre"],
    "price": 350,
    "hotel_name": "Le Marais",
    "estimated_duration": 2,
    "stars": 4,
    "meal_plan": "petit_dejeuner",
    "num_people": 2,
    "departure_city": "Bruxelles"
}

Input: "Séjour all inclusive à Marrakech, vol depuis Bruxelles, 5 étoiles, 600€ par personne"
Output: {
    "destination": "Marrakech, Maroc",
    "transport_type": "avion",
    "is_day_trip": false,
    "activities": ["Médina de Marrakech", "Jardin Majorelle", "Place Jemaa el-Fna"],
    "price": 600,
    "hotel_name": null,
    "estimated_duration": 7,
    "stars": 5,
    "meal_plan": "all_in",
    "num_people": 1,
    "departure_city": "Bruxelles"
}

Input: "Circuit autocar en Toscane, 5 jours, Florence + Pise + Sienne, 400€"
Output: {
    "destination": "Toscane, Italie",
    "transport_type": "autocar",
    "is_day_trip": false,
    "activities": ["Florence", "Pise", "Sienne"],
    "price": 400,
    "hotel_name": null,
    "estimated_duration": 5,
    "stars": 3,
    "meal_plan": "demi_pension",
    "num_people": 2,
    "departure_city": null
}

IMPORTANT : Réponds UNIQUEMENT en JSON valide, sans markdown (pas de ```json), sans texte additionnel.
Le JSON doit être directement parseable.
"""
        
        full_prompt = system_prompt + f"\n\nPrompt utilisateur: {prompt}"
        
        try:
            response = self.model.generate_content(full_prompt)
            response_text = response.text.strip()
            
            # Nettoyer la réponse si elle contient des markdown
            response_text = re.sub(r'^```json\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
            
            # Parser le JSON
            parsed = json.loads(response_text)
            
            # Validation et nettoyage
            return self._validate_and_clean_parsed_data(parsed)
            
        except json.JSONDecodeError as e:
            print(f"❌ Erreur de parsing JSON: {e}")
            print(f"Réponse brute: {response.text}")
            return {
                "error": "Impossible de parser le prompt. Veuillez reformuler.",
                "raw_response": response.text,
                "success": False
            }
        except Exception as e:
            print(f"❌ Erreur Gemini API: {e}")
            return {
                "error": f"Erreur de l'API IA: {str(e)}",
                "success": False
            }
    
    def _validate_and_clean_parsed_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valide et nettoie les données parsées
        
        Args:
            data: Données brutes de l'IA
            
        Returns:
            Données validées et nettoyées
        """
        
        # Champs obligatoires
        required_fields = ['destination', 'transport_type', 'is_day_trip']
        for field in required_fields:
            if field not in data:
                data[field] = None if field != 'is_day_trip' else False
        
        # Validation transport_type
        valid_transports = ['avion', 'train', 'autocar', 'voiture']
        if data.get('transport_type') not in valid_transports:
            data['transport_type'] = 'avion'  # Par défaut
        
        # Validation meal_plan
        valid_meal_plans = ['logement_seul', 'petit_dejeuner', 'demi_pension', 
                           'pension_complete', 'all_in']
        if data.get('meal_plan') and data['meal_plan'] not in valid_meal_plans:
            data['meal_plan'] = None
        
        # Validation stars
        if data.get('stars'):
            try:
                stars = int(data['stars'])
                data['stars'] = max(1, min(5, stars))  # Entre 1 et 5
            except (ValueError, TypeError):
                data['stars'] = 3  # Par défaut
        
        # Validation price
        if data.get('price'):
            try:
                data['price'] = float(data['price'])
            except (ValueError, TypeError):
                data['price'] = None
        
        # Validation estimated_duration
        if data.get('estimated_duration'):
            try:
                data['estimated_duration'] = int(data['estimated_duration'])
            except (ValueError, TypeError):
                data['estimated_duration'] = 3
        
        # Validation num_people
        if data.get('num_people'):
            try:
                data['num_people'] = int(data['num_people'])
            except (ValueError, TypeError):
                data['num_people'] = 2
        else:
            data['num_people'] = 2
        
        # Validation activities (doit être une liste)
        if not isinstance(data.get('activities'), list):
            data['activities'] = []
        
        # Marquer comme succès
        data['success'] = True
        
        return data
    
    def generate_day_trip_program(self, 
                                  destination: str, 
                                  activities: List[str],
                                  departure_time: str = "08:00",
                                  return_time: str = "20:00",
                                  departure_address: str = "Bruxelles") -> List[Dict[str, str]]:
        """
        Génère un programme horaire détaillé pour une excursion d'un jour
        
        Args:
            destination: Ville de destination
            activities: Liste des activités prévues
            departure_time: Heure de départ (format HH:MM)
            return_time: Heure de retour (format HH:MM)
            departure_address: Lieu de départ
            
        Returns:
            Liste de dict avec {"time": "HH:MM", "activity": "Description"}
            
        Example:
            [
                {"time": "08:00", "activity": "Départ de Bruxelles"},
                {"time": "10:00", "activity": "Pause café"},
                {"time": "11:30", "activity": "Arrivée à Rome"},
                ...
            ]
        """
        
        activities_str = ", ".join(activities) if activities else "visite de la ville"
        
        prompt = f"""
Crée un programme horaire détaillé et réaliste pour une excursion d'un jour à {destination}.

CONTRAINTES :
- Heure de départ : {departure_time} depuis {departure_address}
- Heure de retour : {return_time} à {departure_address}
- Activités à inclure : {activities_str}

Le programme doit être réaliste et inclure :
1. Temps de trajet aller (adapter selon la distance)
2. Au moins une pause en route (café, repos)
3. Temps de visite raisonnable pour chaque activité (1h-2h par site)
4. Pause déjeuner (environ 1h-1h30)
5. Temps libre pour shopping/découverte personnelle
6. Temps de trajet retour

RÈGLES IMPORTANTES :
- Les heures doivent être dans l'ordre chronologique
- Prévoir des temps réalistes entre chaque activité
- Total de temps doit correspondre à {departure_time} → {return_time}
- Maximum 8-10 étapes dans la journée

Format de sortie : JSON array avec {{"time": "HH:MM", "activity": "Description"}}

EXEMPLE de sortie attendue :
[
    {{"time": "08:00", "activity": "Départ de {departure_address}"}},
    {{"time": "10:30", "activity": "Pause café et repos"}},
    {{"time": "11:30", "activity": "Arrivée à {destination}"}},
    {{"time": "12:00", "activity": "Visite guidée de [Premier lieu]"}},
    {{"time": "13:30", "activity": "Déjeuner libre"}},
    {{"time": "15:00", "activity": "Visite de [Deuxième lieu]"}},
    {{"time": "16:30", "activity": "Temps libre et shopping"}},
    {{"time": "17:30", "activity": "Départ retour vers {departure_address}"}},
    {{"time": "{return_time}", "activity": "Arrivée à {departure_address}"}}
]

Réponds UNIQUEMENT en JSON valide, sans markdown, sans texte additionnel.
"""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Nettoyer la réponse
            response_text = re.sub(r'^```json\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
            
            program = json.loads(response_text)
            
            # Validation : doit être une liste
            if not isinstance(program, list):
                raise ValueError("Le programme n'est pas une liste")
            
            # Validation : chaque élément doit avoir time et activity
            for item in program:
                if not isinstance(item, dict) or 'time' not in item or 'activity' not in item:
                    raise ValueError("Format de programme invalide")
            
            return program
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"❌ Erreur parsing programme: {e}")
            print(f"Réponse brute: {response.text}")
            
            # Programme par défaut en cas d'erreur
            return self._generate_default_program(
                destination, 
                activities, 
                departure_time, 
                return_time,
                departure_address
            )
        except Exception as e:
            print(f"❌ Erreur Gemini API: {e}")
            return self._generate_default_program(
                destination, 
                activities, 
                departure_time, 
                return_time,
                departure_address
            )
    
    def _generate_default_program(self,
                                  destination: str,
                                  activities: List[str],
                                  departure_time: str,
                                  return_time: str,
                                  departure_address: str) -> List[Dict[str, str]]:
        """
        Génère un programme par défaut si l'IA échoue
        
        Returns:
            Programme basique mais fonctionnel
        """
        
        program = [
            {"time": departure_time, "activity": f"Départ de {departure_address}"},
            {"time": "10:30", "activity": "Pause café"},
            {"time": "12:00", "activity": f"Arrivée à {destination}"},
            {"time": "12:30", "activity": "Déjeuner libre"},
        ]
        
        # Ajouter les activités
        current_time = "14:00"
        for i, activity in enumerate(activities[:3]):  # Max 3 activités
            hour = 14 + (i * 2)
            program.append({
                "time": f"{hour:02d}:00",
                "activity": f"Visite de {activity}"
            })
            current_time = f"{hour + 1:02d}:30"
        
        # Temps libre et retour
        program.extend([
            {"time": current_time, "activity": "Temps libre"},
            {"time": "17:30", "activity": f"Départ retour vers {departure_address}"},
            {"time": return_time, "activity": f"Arrivée à {departure_address}"}
        ])
        
        return program
    
    def suggest_activities(self, destination: str, max_suggestions: int = 5) -> List[str]:
        """
        Suggère des activités populaires pour une destination
        
        Args:
            destination: Ville de destination
            max_suggestions: Nombre maximum de suggestions
            
        Returns:
            Liste d'activités suggérées
        """
        
        prompt = f"""
Liste les {max_suggestions} attractions/activités touristiques les plus populaires à {destination}.

Format : JSON array de strings, sans numérotation.

Exemple pour Paris :
["Tour Eiffel", "Musée du Louvre", "Arc de Triomphe", "Montmartre", "Cathédrale Notre-Dame"]

Réponds UNIQUEMENT en JSON valide, sans markdown, sans texte additionnel.
Destination : {destination}
"""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Nettoyer
            response_text = re.sub(r'^```json\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
            
            suggestions = json.loads(response_text)
            
            if isinstance(suggestions, list):
                return suggestions[:max_suggestions]
            else:
                return []
                
        except Exception as e:
            print(f"❌ Erreur suggestions: {e}")
            return []
    
    def estimate_travel_duration(self, 
                                origin: str, 
                                destination: str,
                                transport_type: str = "autocar") -> int:
        """
        Estime la durée de trajet en minutes
        
        Args:
            origin: Ville de départ
            destination: Ville d'arrivée
            transport_type: Type de transport
            
        Returns:
            Durée estimée en minutes
        """
        
        prompt = f"""
Estime la durée de trajet en {transport_type} de {origin} à {destination}.

Prends en compte :
- Distance réelle
- Conditions de circulation normales
- Pauses éventuelles pour les longs trajets

Réponds UNIQUEMENT avec un nombre entier représentant les minutes.
Exemple : 450 (pour 7h30)

Pas de texte, pas de markdown, juste le nombre.
"""
        
        try:
            response = self.model.generate_content(prompt)
            duration_str = response.text.strip()
            
            # Extraire le nombre
            duration = int(re.search(r'\d+', duration_str).group())
            
            return duration
            
        except Exception as e:
            print(f"❌ Erreur estimation durée: {e}")
            # Durée par défaut selon le transport
            defaults = {
                'autocar': 480,  # 8h
                'train': 300,    # 5h
                'avion': 120,    # 2h
                'voiture': 360   # 6h
            }
            return defaults.get(transport_type, 360)


# ==============================================================================
# FONCTIONS UTILITAIRES GLOBALES
# ==============================================================================

def parse_prompt(prompt: str, gemini_api_key: str) -> Dict[str, Any]:
    """
    Fonction raccourci pour parser un prompt
    
    Args:
        prompt: Description du voyage
        gemini_api_key: Clé API Gemini
        
    Returns:
        Données structurées du voyage
    """
    assistant = AIAssistant(gemini_api_key)
    return assistant.parse_travel_prompt(prompt)


def generate_program(destination: str,
                     activities: List[str],
                     departure_time: str,
                     return_time: str,
                     gemini_api_key: str,
                     departure_address: str = "Bruxelles") -> List[Dict[str, str]]:
    """
    Fonction raccourci pour générer un programme
    
    Args:
        destination: Ville de destination
        activities: Liste d'activités
        departure_time: Heure de départ
        return_time: Heure de retour
        gemini_api_key: Clé API Gemini
        departure_address: Lieu de départ
        
    Returns:
        Programme horaire détaillé
    """
    assistant = AIAssistant(gemini_api_key)
    return assistant.generate_day_trip_program(
        destination,
        activities,
        departure_time,
        return_time,
        departure_address
    )


# ==============================================================================
# EXEMPLE D'UTILISATION
# ==============================================================================

if __name__ == "__main__":
    """
    Tests du service AI Assistant
    Lancez : python services/ai_assistant.py
    """
    
    import os
    
    # Récupérer la clé depuis l'environnement
    API_KEY = os.environ.get('GOOGLE_GEMINI_API_KEY')
    
    if not API_KEY:
        print("❌ Clé GOOGLE_GEMINI_API_KEY manquante dans .env")
        exit(1)
    
    assistant = AIAssistant(API_KEY)
    
    # Test 1 : Parse de prompts
    print("\n" + "="*60)
    print("TEST 1 : PARSING DE PROMPTS")
    print("="*60)
    
    test_prompts = [
        "Voyage en autocar à Rome, excursion Colisée + Vatican, 100€",
        "Excursion d'une journée à Bruges, 50€",
        "Week-end Paris, train, 4 étoiles, 350€",
        "Séjour all-in Marrakech, 5★, vol Bruxelles, 600€"
    ]
    
    for prompt in test_prompts:
        print(f"\n📝 Prompt: {prompt}")
        result = assistant.parse_travel_prompt(prompt)
        print(f"✅ Résultat: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    # Test 2 : Génération de programme
    print("\n" + "="*60)
    print("TEST 2 : GÉNÉRATION DE PROGRAMME")
    print("="*60)
    
    program = assistant.generate_day_trip_program(
        destination="Bruges",
        activities=["Grand-Place", "Béguinage", "Canaux"],
        departure_time="08:00",
        return_time="20:00"
    )
    
    print("\n📋 Programme généré:")
    for step in program:
        print(f"  {step['time']} - {step['activity']}")
    
    # Test 3 : Suggestions d'activités
    print("\n" + "="*60)
    print("TEST 3 : SUGGESTIONS D'ACTIVITÉS")
    print("="*60)
    
    suggestions = assistant.suggest_activities("Barcelone")
    print(f"\n🎯 Suggestions pour Barcelone: {suggestions}")
    
    print("\n✅ Tests terminés !")
