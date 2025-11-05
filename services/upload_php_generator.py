# services/upload_php_generator.py
"""
Générateur de fichier upload.php personnalisé pour chaque agence.
Ce fichier permet de contourner les blocages FTP depuis Railway vers Hostinger.
"""

def generate_upload_php(agency_domain: str, api_key: str, base_path: str) -> str:
    """
    Génère le contenu du fichier upload.php personnalisé pour une agence.
    
    Args:
        agency_domain: Domaine de l'agence (ex: voyages-privileges.be)
        api_key: Clé API secrète pour sécuriser les uploads
        base_path: Chemin absolu sur le serveur (ex: /home/uXXX/domains/agence.com/public_html/)
    
    Returns:
        str: Contenu PHP du fichier upload.php
    """
    
    php_content = f'''<?php
/**
 * API de Publication Odyssée - Fichier upload.php
 * Généré automatiquement pour : {agency_domain}
 * 
 * Ce fichier permet de publier des fiches de voyage depuis l'application Odyssée
 * hébergée sur Railway vers votre hébergement Hostinger (ou autre).
 * 
 * Installation :
 * 1. Uploadez ce fichier à la racine de votre site web via FTP
 * 2. Assurez-vous que le dossier cible a les bonnes permissions (755)
 * 3. Testez l'API en accédant à https://www.{agency_domain}/upload.php
 * 
 * Sécurité :
 * - Clé API : {api_key}
 * - Ne partagez JAMAIS cette clé API
 * - Utilisez HTTPS uniquement
 */

error_reporting(0);
ini_set('display_errors', 0);

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, X-Api-Key');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {{
    http_response_code(200);
    exit();
}}

// Récupération des données
$input = json_decode(file_get_contents('php://input'), true);

// Authentification via le corps JSON ou l'en-tête
$api_key = $input['api_key'] ?? ($_SERVER['HTTP_X_API_KEY'] ?? '');

// ⚠️ IMPORTANT : Changez cette clé API si nécessaire
if ($api_key !== '{api_key}') {{
    http_response_code(401);
    echo json_encode(['success' => false, 'message' => 'Clé API invalide']);
    exit();
}}

// ⚠️ IMPORTANT : Vérifiez et ajustez ce chemin selon votre hébergement
// Pour Hostinger, le chemin est généralement : /home/uXXXXXXXXX/domains/VOTRE-DOMAINE/public_html/
$base_path = '{base_path}';

switch ($_SERVER['REQUEST_METHOD']) {{
    case 'GET':
        // Test de connexion
        echo json_encode([
            'success' => true,
            'message' => 'API Odyssée connectée',
            'domain' => '{agency_domain}',
            'php_version' => phpversion(),
            'timestamp' => date('Y-m-d H:i:s')
        ]);
        break;

    case 'POST':
        // Upload de fichier
        if (!isset($input['filename']) || !isset($input['content']) || !isset($input['directory'])) {{
            http_response_code(400);
            echo json_encode(['success' => false, 'message' => 'Données manquantes (filename, content, directory)']);
            exit();
        }}
        
        $filename = basename($input['filename']);
        $content = base64_decode($input['content']);
        $directory = trim($input['directory'], '/');
        
        // Créer le chemin complet
        $full_dir = $base_path . $directory;
        if (!is_dir($full_dir)) {{
            if (!mkdir($full_dir, 0755, true)) {{
                http_response_code(500);
                echo json_encode(['success' => false, 'message' => 'Impossible de créer le répertoire: ' . $full_dir]);
                exit();
            }}
        }}
        
        // Écrire le fichier
        $file_path = $full_dir . '/' . $filename;
        if (file_put_contents($file_path, $content) !== false) {{
            $url = 'https://www.{agency_domain}/' . $directory . '/' . $filename;
            echo json_encode([
                'success' => true,
                'message' => 'Fichier uploadé avec succès',
                'url' => $url,
                'filename' => $filename
            ]);
        }} else {{
            http_response_code(500);
            echo json_encode(['success' => false, 'message' => 'Erreur lors de l\\'écriture du fichier']);
        }}
        break;

    case 'DELETE':
        // Suppression de fichier
        if (!isset($input['filename']) || !isset($input['directory'])) {{
            http_response_code(400);
            echo json_encode(['success' => false, 'message' => 'Données manquantes pour suppression']);
            exit();
        }}
        
        $filename = basename($input['filename']);
        $directory = trim($input['directory'], '/');
        $file_path = $base_path . $directory . '/' . $filename;
        
        if (file_exists($file_path)) {{
            if (unlink($file_path)) {{
                echo json_encode(['success' => true, 'message' => 'Fichier supprimé avec succès']);
            }} else {{
                http_response_code(500);
                echo json_encode(['success' => false, 'message' => 'Impossible de supprimer le fichier']);
            }}
        }} else {{
            echo json_encode(['success' => true, 'message' => 'Fichier déjà absent']);
        }}
        break;

    default:
        http_response_code(405);
        echo json_encode(['success' => false, 'message' => 'Méthode non autorisée']);
        break;
}}
?>'''
    
    return php_content
