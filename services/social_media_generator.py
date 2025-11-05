import os
import json
import requests
from datetime import datetime
from typing import List, Dict

class SocialMediaGenerator:
    """
    Generates professional social media posts for travel packages.
    Creates Instagram/Facebook carousels with hero images, hotel photos, and attractions.
    """
    
    def __init__(self, agency, trip, google_api_key, bannerbear_config: Dict[str, str]):
        self.agency = agency
        self.trip = trip
        self.google_api_key = google_api_key
        if not all(bannerbear_config.get(k) for k in ['api_key', 'hero_template_id', 'service_template_id']):
            raise ValueError("La configuration Bannerbear (clé API et IDs de template) est incomplète.")
        
        self.api_key = bannerbear_config['api_key']
        self.hero_template_id = bannerbear_config['hero_template_id']
        self.service_template_id = bannerbear_config['service_template_id']
        self.api_base_url = 'https://api.bannerbear.com/v2'
        
        # Design settings
        self.primary_color = agency.primary_color or '#3498db'
        self.secondary_color = agency.secondary_color or '#2c3e50'

        # Parse full_data_json once to use in multiple methods
        try:
            self.full_data = json.loads(self.trip.full_data_json)
            self.form_data = self.full_data.get('form_data', {})
        except (json.JSONDecodeError, TypeError):
            self.full_data = {}
            self.form_data = {}
    
    def _get_duration(self) -> int:
        """Helper to get trip duration in days."""
        try:
            if self.trip.is_day_trip:
                return 1
            
            date_start = datetime.strptime(self.form_data['date_start'], '%Y-%m-%d')
            date_end = datetime.strptime(self.form_data['date_end'], '%Y-%m-%d')
            duration = (date_end - date_start).days
            return duration if duration > 0 else 1
        except (KeyError, ValueError):
            return 7

    def generate_instagram_carousel(self) -> Dict:
        """
        Generate a complete Instagram carousel campaign for regular trips (sejours).
        Returns dict with slides and captions.
        """
        
        print(f"🎨 Generating Instagram carousel for {self.trip.destination}...")
        
        # 1. Préparer les données pour chaque slide
        hero_modifications = self._get_hero_slide_data()
        service_modifications = self._get_service_slide_data()

        # 2. Appeler l'API Bannerbear pour générer les deux images
        hero_image = self._create_bannerbear_image(self.hero_template_id, hero_modifications)
        service_image = self._create_bannerbear_image(self.service_template_id, service_modifications)
        images = [hero_image, service_image]
        
        # 3. Traiter la réponse : télécharger et sauvegarder les images
        slides = self._process_bannerbear_images(images)
        
        # 4. Generate captions
        captions = self._generate_captions()
        
        # 5. Save campaign to database
        campaign_data = {
            'slides': slides,
            'captions': captions,
            'hashtags': self._generate_hashtags(),
            'created_at': datetime.utcnow().isoformat()
        }
        
        return campaign_data
    
    def generate_day_trip_post(self, description: str, day_trip_template_id: str) -> Dict:
        """
        Generate an Instagram post for a day trip based on a text description.
        Uses Gemini AI to parse and format the description.
        
        Args:
            description: Raw text description of the day trip
            day_trip_template_id: Bannerbear template ID for day trips
        
        Returns:
            Dict with slide data and captions
        """
        
        print(f"🎨 Generating day trip post for {self.trip.destination}...")
        print(f"📝 Description: {description[:100]}...")
        
        # 1. Parse the description with Gemini AI
        from services.ai_assistant import AIAssistant
        
        if not self.google_api_key:
            raise ValueError("Google API key required for day trip generation")
        
        ai = AIAssistant(self.google_api_key)
        parsed_data = ai.parse_day_trip_description(description)
        
        if not parsed_data.get('success'):
            raise Exception(f"Failed to parse description: {parsed_data.get('error', 'Unknown error')}")
        
        print(f"✅ AI parsed successfully: {parsed_data.get('title')}")
        
        # 2. Get background image
        main_image_url = None
        if self.full_data.get('api_data', {}).get('photos'):
            main_image_url = self.full_data['api_data']['photos'][0]
        
        # 3. Prepare modifications for Bannerbear template
        modifications = [
            {"name": "background_image", "image_url": main_image_url},
            {"name": "title", "text": parsed_data['title']},
            {"name": "subtitle", "text": parsed_data['subtitle']},
            {"name": "highlights", "text": "\n".join(parsed_data['highlights'])},
            {"name": "departure_info", "text": parsed_data['departure_info']},
            {"name": "description", "text": parsed_data['formatted_description']},
            {"name": "price", "text": f"{self.trip.price}€" if self.trip.price else "Sur demande"}
        ]
        
        # 4. Generate image with Bannerbear
        print(f"🎨 Calling Bannerbear with template: {day_trip_template_id}")
        image_data = self._create_bannerbear_image(day_trip_template_id, modifications)
        
        # 5. Process and save image
        slides = self._process_bannerbear_images([image_data])
        
        # 6. Generate caption using parsed data
        caption = self._generate_day_trip_caption(parsed_data)
        
        # 7. Return campaign data
        campaign_data = {
            'slides': slides,
            'captions': {
                'instagram': caption,
                'facebook': caption  # Same caption for both platforms
            },
            'hashtags': self._generate_hashtags(),
            'created_at': datetime.utcnow().isoformat(),
            'ai_parsed_data': parsed_data  # Include AI-parsed data for reference
        }
        
        return campaign_data
    
    def _create_bannerbear_image(self, template_id: str, modifications: List[Dict]) -> Dict:
        """Crée une image via l'API REST Bannerbear"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'template': template_id,
            'modifications': modifications
        }
        
        print(f"🔍 Bannerbear API Request:")
        print(f"   Template ID: {template_id}")
        print(f"   API Key: {self.api_key[:10]}...")
        print(f"   Modifications: {len(modifications)} items")
        
        response = requests.post(
            f'{self.api_base_url}/images',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        # Log pour debug
        if response.status_code != 200 and response.status_code != 202:
            print(f"❌ Bannerbear API Error: {response.status_code}")
            print(f"Response: {response.text}")
            print(f"\n⚠️  VÉRIFIEZ:")
            print(f"   1. Que la clé API est valide")
            print(f"   2. Que '{template_id}' est un UID de template valide (format: alphanumerique 18 caractères)")
            print(f"   3. Que le template existe dans votre projet Bannerbear")
            raise Exception(f"Bannerbear API Error {response.status_code}: {response.text}")
        
        response.raise_for_status()
        
        image_data = response.json()
        
        # Poll for completion if not synchronous
        if image_data.get('status') == 'pending':
            image_uid = image_data['uid']
            import time
            max_attempts = 30
            for _ in range(max_attempts):
                time.sleep(2)
                status_response = requests.get(
                    f'{self.api_base_url}/images/{image_uid}',
                    headers=headers
                )
                status_data = status_response.json()
                if status_data.get('status') == 'completed':
                    return status_data
            raise Exception("Timeout waiting for Bannerbear image generation")
        
        return image_data
    
    def _process_bannerbear_images(self, images: List[Dict]) -> List[Dict]:
        """Traite la réponse de Bannerbear pour la sauvegarder et la formater."""
        processed_slides = []
        for i, image_data in enumerate(images):
            image_url = image_data['image_url_png']
            
            # Télécharger l'image
            response = requests.get(image_url)
            if response.status_code == 200:
                # Sauvegarder l'image localement
                slide_path = f"static/campaigns/{self.trip.id}_slide_{i}.png"
                os.makedirs(os.path.dirname(slide_path), exist_ok=True)
                with open(slide_path, 'wb') as f:
                    f.write(response.content)
                
                processed_slides.append({
                    'type': 'bannerbear_slide',
                    'path': slide_path,
                    'url': f"/{slide_path}",
                    'index': i
                })
        return processed_slides

    def _get_hero_slide_data(self) -> List[Dict]:
        """Prépare les données pour le slide de présentation."""
        main_image_url = None
        if self.full_data.get('api_data', {}).get('photos'):
            main_image_url = self.full_data['api_data']['photos'][0]
        
        duration = self._get_duration()
        stars = int(self.form_data.get('stars', 0))
        num_people = int(self.form_data.get('num_people', 2))
        
        # Nettoyer le nom de l'hôtel (enlever l'adresse si présente)
        hotel_name = self.trip.hotel_name
        if ',' in hotel_name:
            # Si l'hôtel contient une virgule, on prend uniquement la partie avant
            hotel_name = hotel_name.split(',')[0].strip()

        return [
            {"name": "background_image", "image_url": main_image_url},
            {"name": "ville", "text": self.trip.destination},
            {"name": "hotelname", "text": hotel_name},
            {"name": "personne", "text": f"{num_people} personne{'s' if num_people > 1 else ''}"},
            {"name": "duree", "text": f"{duration} jour{'s' if duration > 1 else ''}"},
            {"name": "prix", "text": f"{self.trip.price}€"},
            {"name": "etoile", "text": "⭐" * stars if stars > 0 else ""},
        ]

    def _get_service_slide_data(self) -> List[Dict]:
        """Prépare les données pour le slide des services."""
        services = []
        
        # Type de logement
        meal_plan_labels = {
            'logement_seul': '🔑 Logement seul',
            'petit_dejeuner': '🥐 Petit-déjeuner',
            'demi_pension': '🍽️ Demi-pension',
            'pension_complete': '🍴 Pension complète',
            'all_in': '🍹 All Inclusive'
        }
        meal_plan = self.form_data.get('meal_plan')
        if meal_plan in meal_plan_labels:
            services.append(meal_plan_labels[meal_plan])

        # Transport
        transport_type = self.form_data.get('transport_type')
        if transport_type == 'avion':
            services.append("✈️ Vol inclus")
        elif transport_type == 'train':
            services.append("🚂 Train inclus")

        # Transfert ou voiture
        if int(self.form_data.get('transfer_cost', 0)) > 0:
            services.append("🚐 Transferts inclus")
        if int(self.form_data.get('car_rental_cost', 0)) > 0:
            services.append("🚗 Voiture de location")

        # Sélectionner une photo de l'hôtel
        hotel_photo_url = None
        api_photos = self.full_data.get('api_data', {}).get('photos', [])
        if len(api_photos) > 1:
            hotel_photo_url = api_photos[1]
        elif api_photos:
            hotel_photo_url = api_photos[0]

        return [
            {"name": "service", "text": "\n".join(services)},
            {"name": "image_container_rectangle_2", "image_url": hotel_photo_url},
        ]
    
    def _generate_captions(self) -> Dict:
        """Generate platform-specific captions"""
        captions = {
            'instagram': self._generate_instagram_caption(),
            'facebook': self._generate_facebook_caption()
        }
        return captions
    
    def _generate_instagram_caption(self) -> str:
        """Generate Instagram-optimized caption"""
        duration = self._get_duration()
        caption = f"""
🌟 {self.trip.destination.upper()} VOUS ATTEND ! 🌟

Découvrez notre offre exceptionnelle :
📍 Destination : {self.trip.destination}
⏱ Durée : {duration} jours
💰 À partir de {self.trip.price}€ par personne

✨ Les points forts :
• Hébergement en hôtel sélectionné
• Visites des sites incontournables
• Assistance francophone
• Vols inclus

📲 Réservez maintenant et vivez une expérience inoubliable !

#Voyage{self.trip.destination.replace(' ', '')} #VoyageOrganise #Tourisme #Vacances #Travel #InstaTravel #TravelGram #Wanderlust #VoyageDeLuxe #DestinationDeReve
        """
        return caption.strip()
    
    def _generate_facebook_caption(self) -> str:
        """Generate Facebook-optimized caption"""
        duration = self._get_duration()
        caption = f"""
🌍 OFFRE EXCEPTIONNELLE - {self.trip.destination} 🌍

Nous sommes ravis de vous présenter notre nouveau voyage organisé vers {self.trip.destination} !

📅 Durée : {duration} jours
💶 Prix : À partir de {self.trip.price}€ par personne (tout inclus)

Ce voyage comprend :
✈️ Les vols aller-retour
🏨 L'hébergement en hôtel de qualité
🚌 Les transferts sur place
🎫 Les visites guidées des principaux sites
🍽 La pension selon programme
👨‍✈️ L'assistance de notre équipe

Ne manquez pas cette opportunité de découvrir {self.trip.destination} dans les meilleures conditions !

Pour plus d'informations ou pour réserver :
📞 Contactez-nous au {getattr(self.agency, 'contact_phone', 'téléphone')}
🌐 Visitez notre site : {getattr(self.agency, 'website_url', 'www.votreagence.com')}

#Voyage #Tourisme #{self.trip.destination.replace(' ', '')} #VacancesDeLuxe #AgenceDeVoyage
        """
        return caption.strip()
    
    def _generate_day_trip_caption(self, parsed_data: Dict) -> str:
        """Generate Instagram caption for day trip using AI-parsed data"""
        caption = f"""
🚌 {parsed_data['title'].upper()} 🚌

{parsed_data['program_summary']}

✨ Ce qui vous attend :
"""
        
        # Add highlights
        for highlight in parsed_data['highlights']:
            caption += f"{highlight}\n"
        
        caption += f"""
{parsed_data['departure_info']}
💰 Prix : {self.trip.price}€ par personne

📞 Réservation obligatoire
🎫 Places limitées !

#Excursion{self.trip.destination.replace(' ', '')} #{self.trip.destination.replace(' ', '')} #Excursion #VoyageDUnJour #DayTrip #Tourisme #Travel #InstaTravel #GroupTravel #BusTrip #{self.agency.name.replace(' ', '')}
        """
        return caption.strip()
    
    def _generate_hashtags(self) -> str:
        """Generate relevant hashtags"""
        destination_tags = self.trip.destination.replace(' ', '').replace('-', '')
        hashtags = [
            f"#Voyage{destination_tags}",
            f"#{destination_tags}",
            "#VoyageOrganise",
            "#Tourisme",
            "#Vacances",
            "#Travel",
            "#InstaTravel",
            "#TravelGram",
            "#Wanderlust",
            "#VoyageDeLuxe",
            "#AgenceDeVoyage",
            f"#{self.agency.name.replace(' ', '')}",
            "#DestinationDeReve",
            "#VoyageEnGroupe",
            "#TourOperator"
        ]
        return " ".join(hashtags)
