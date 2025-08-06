#!/usr/bin/env python3
"""
DGA (Domain Generation Algorithm) Classifier Module
Uses machine learning to detect algorithmically generated domains
"""

import re
import logging
import pickle
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import Counter
import string
import math
from dataclasses import dataclass

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn not available. DGA detection will use heuristics only.")

@dataclass
class DGAResult:
    """Result of DGA classification"""
    domain: str
    is_dga: bool
    confidence: float
    features: Dict
    algorithm: str
    reason: str

class DGAClassifier:
    def __init__(self, model_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.vectorizer = None
        self.model_path = model_path
        
        # Load model if available
        if model_path and SKLEARN_AVAILABLE:
            self._load_model()
        
        # Known DGA families patterns
        self.dga_patterns = {
            'conficker': r'^[a-z]{6,12}\.(?:com|net|org|info|biz)$',
            'zeus': r'^[a-z0-9]{10,20}\.(?:com|net|org)$',
            'cryptolocker': r'^[a-z]{12,16}\.(?:com|net|org|info)$',
            'necurs': r'^[a-z]{6,15}[0-9]{0,3}\.(?:com|net|org)$',
        }
        
    def _load_model(self):
        """Load pre-trained model"""
        try:
            with open(self.model_path, 'rb') as f:
                model_data = pickle.load(f)
                self.model = model_data['model']
                self.vectorizer = model_data['vectorizer']
            self.logger.info("DGA model loaded successfully")
        except FileNotFoundError:
            self.logger.warning(f"Model file not found: {self.model_path}")
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            
    def extract_features(self, domain: str) -> Dict:
        """Extract features from domain for classification"""
        # Remove TLD for analysis
        domain_parts = domain.split('.')
        if len(domain_parts) > 1:
            domain_name = domain_parts[0]
        else:
            domain_name = domain
            
        features = {}
        
        # Length features
        features['length'] = len(domain_name)
        features['total_length'] = len(domain)
        
        # Character composition
        features['digit_count'] = sum(c.isdigit() for c in domain_name)
        features['alpha_count'] = sum(c.isalpha() for c in domain_name)
        features['special_count'] = sum(not c.isalnum() for c in domain_name)
        features['digit_ratio'] = features['digit_count'] / len(domain_name) if domain_name else 0
        
        # Vowel/consonant analysis
        vowels = 'aeiou'
        features['vowel_count'] = sum(c.lower() in vowels for c in domain_name)
        features['consonant_count'] = features['alpha_count'] - features['vowel_count']
        features['vowel_ratio'] = features['vowel_count'] / features['alpha_count'] if features['alpha_count'] else 0
        
        # N-gram analysis
        features['bigram_entropy'] = self._calculate_ngram_entropy(domain_name, 2)
        features['trigram_entropy'] = self._calculate_ngram_entropy(domain_name, 3)
        
        # Dictionary word presence
        features['dict_words'] = self._count_dictionary_words(domain_name)
        features['pronounceable_score'] = self._calculate_pronounceable_score(domain_name)
        
        # Pattern analysis
        features['consecutive_consonants'] = self._max_consecutive_consonants(domain_name)
        features['consecutive_digits'] = self._max_consecutive_digits(domain_name)
        features['char_diversity'] = len(set(domain_name.lower()))
        
        # TLD analysis
        if len(domain_parts) > 1:
            tld = domain_parts[-1].lower()
            features['tld'] = tld
            features['suspicious_tld'] = tld in ['tk', 'ml', 'ga', 'cf', 'info', 'biz']
        else:
            features['tld'] = ''
            features['suspicious_tld'] = False
            
        # Frequency analysis
        features['char_frequency_variance'] = self._calculate_char_frequency_variance(domain_name)
        
        return features
        
    def _calculate_ngram_entropy(self, text: str, n: int) -> float:
        """Calculate entropy of n-grams in text"""
        if len(text) < n:
            return 0.0
            
        ngrams = [text[i:i+n] for i in range(len(text) - n + 1)]
        ngram_counts = Counter(ngrams)
        total = len(ngrams)
        
        entropy = 0.0
        for count in ngram_counts.values():
            prob = count / total
            if prob > 0:
                entropy -= prob * math.log2(prob)
                
        return entropy
        
    def _count_dictionary_words(self, domain: str) -> int:
        """Count dictionary words in domain (simplified)"""
        # Common English words that might appear in legitimate domains
        common_words = {
            'mail', 'www', 'web', 'ftp', 'blog', 'news', 'shop', 'store', 
            'home', 'info', 'help', 'support', 'admin', 'user', 'login',
            'secure', 'safe', 'tech', 'data', 'cloud', 'server', 'host',
            'app', 'api', 'dev', 'test', 'demo', 'beta', 'alpha'
        }
        
        domain_lower = domain.lower()
        word_count = 0
        
        for word in common_words:
            if word in domain_lower:
                word_count += 1
                
        return word_count
        
    def _calculate_pronounceable_score(self, domain: str) -> float:
        """Calculate how pronounceable a domain is"""
        if not domain:
            return 0.0
            
        vowels = 'aeiou'
        consonants = 'bcdfghjklmnpqrstvwxyz'
        
        # Check for alternating vowel-consonant patterns
        alternations = 0
        for i in range(len(domain) - 1):
            curr_char = domain[i].lower()
            next_char = domain[i + 1].lower()
            
            if ((curr_char in vowels and next_char in consonants) or 
                (curr_char in consonants and next_char in vowels)):
                alternations += 1
                
        return alternations / (len(domain) - 1) if len(domain) > 1 else 0
        
    def _max_consecutive_consonants(self, domain: str) -> int:
        """Find maximum consecutive consonants"""
        consonants = 'bcdfghjklmnpqrstvwxyz'
        max_consecutive = 0
        current_consecutive = 0
        
        for char in domain.lower():
            if char in consonants:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
                
        return max_consecutive
        
    def _max_consecutive_digits(self, domain: str) -> int:
        """Find maximum consecutive digits"""
        max_consecutive = 0
        current_consecutive = 0
        
        for char in domain:
            if char.isdigit():
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
                
        return max_consecutive
        
    def _calculate_char_frequency_variance(self, domain: str) -> float:
        """Calculate variance in character frequency"""
        if not domain:
            return 0.0
            
        char_counts = Counter(domain.lower())
        frequencies = list(char_counts.values())
        
        if len(frequencies) <= 1:
            return 0.0
            
        mean_freq = sum(frequencies) / len(frequencies)
        variance = sum((f - mean_freq) ** 2 for f in frequencies) / len(frequencies)
        
        return variance
        
    def classify_domain_heuristic(self, domain: str) -> DGAResult:
        """Classify domain using heuristic rules"""
        features = self.extract_features(domain)
        
        # Scoring system
        dga_score = 0.0
        reasons = []
        
        # Length-based scoring
        if features['length'] > 15:
            dga_score += 0.3
            reasons.append("very_long_domain")
        elif features['length'] < 4:
            dga_score += 0.2
            reasons.append("very_short_domain")
            
        # Character composition
        if features['digit_ratio'] > 0.3:
            dga_score += 0.4
            reasons.append("high_digit_ratio")
            
        if features['vowel_ratio'] < 0.15:
            dga_score += 0.5
            reasons.append("low_vowel_ratio")
        elif features['vowel_ratio'] > 0.7:
            dga_score += 0.3
            reasons.append("high_vowel_ratio")
            
        # Pattern analysis
        if features['consecutive_consonants'] > 4:
            dga_score += 0.4
            reasons.append("many_consecutive_consonants")
            
        if features['consecutive_digits'] > 3:
            dga_score += 0.3
            reasons.append("many_consecutive_digits")
            
        # Entropy analysis
        if features['bigram_entropy'] > 3.5:
            dga_score += 0.3
            reasons.append("high_bigram_entropy")
            
        # Dictionary words
        if features['dict_words'] == 0 and features['length'] > 6:
            dga_score += 0.2
            reasons.append("no_dictionary_words")
            
        # Pronounceability
        if features['pronounceable_score'] < 0.2:
            dga_score += 0.3
            reasons.append("low_pronounceability")
            
        # TLD analysis
        if features['suspicious_tld']:
            dga_score += 0.2
            reasons.append("suspicious_tld")
            
        # Check against known DGA patterns
        for family, pattern in self.dga_patterns.items():
            if re.match(pattern, domain.lower()):
                dga_score += 0.8
                reasons.append(f"matches_{family}_pattern")
                break
                
        # Normalize score
        confidence = min(dga_score, 1.0)
        is_dga = confidence > 0.5
        
        return DGAResult(
            domain=domain,
            is_dga=is_dga,
            confidence=confidence,
            features=features,
            algorithm='heuristic',
            reason=', '.join(reasons) if reasons else 'legitimate_pattern'
        )
        
    def classify_domain_ml(self, domain: str) -> DGAResult:
        """Classify domain using machine learning model"""
        if not self.model or not self.vectorizer:
            return self.classify_domain_heuristic(domain)
            
        try:
            # Vectorize domain
            domain_vector = self.vectorizer.transform([domain])
            
            # Predict
            prediction = self.model.predict(domain_vector)[0]
            confidence = max(self.model.predict_proba(domain_vector)[0])
            
            features = self.extract_features(domain)
            
            return DGAResult(
                domain=domain,
                is_dga=bool(prediction),
                confidence=confidence,
                features=features,
                algorithm='machine_learning',
                reason='ml_classification'
            )
            
        except Exception as e:
            self.logger.error(f"ML classification failed: {e}")
            return self.classify_domain_heuristic(domain)
            
    def classify_domain(self, domain: str) -> DGAResult:
        """Classify domain (use ML if available, otherwise heuristics)"""
        if self.model and SKLEARN_AVAILABLE:
            return self.classify_domain_ml(domain)
        else:
            return self.classify_domain_heuristic(domain)
            
    def classify_domains_batch(self, domains: List[str]) -> List[DGAResult]:
        """Classify multiple domains"""
        results = []
        for domain in domains:
            results.append(self.classify_domain(domain))
        return results
        
    def train_model(self, legitimate_domains: List[str], dga_domains: List[str], 
                   save_path: Optional[str] = None) -> Dict:
        """Train a new DGA detection model"""
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn required for model training")
            
        # Prepare training data
        all_domains = legitimate_domains + dga_domains
        labels = [0] * len(legitimate_domains) + [1] * len(dga_domains)
        
        # Create feature vectors
        self.vectorizer = TfidfVectorizer(
            analyzer='char',
            ngram_range=(2, 4),
            max_features=10000,
            lowercase=True
        )
        
        X = self.vectorizer.fit_transform(all_domains)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, labels, test_size=0.2, random_state=42, stratify=labels
        )
        
        # Train model
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        report = classification_report(y_test, y_pred, output_dict=True)
        
        # Save model
        if save_path:
            self._save_model(save_path)
            
        self.logger.info("DGA model trained successfully")
        return report
        
    def _save_model(self, path: str):
        """Save trained model"""
        try:
            model_data = {
                'model': self.model,
                'vectorizer': self.vectorizer
            }
            with open(path, 'wb') as f:
                pickle.dump(model_data, f)
            self.logger.info(f"Model saved to {path}")
        except Exception as e:
            self.logger.error(f"Error saving model: {e}")
            
    def get_feature_importance(self) -> Dict:
        """Get feature importance from trained model"""
        if not self.model:
            return {}
            
        try:
            feature_names = self.vectorizer.get_feature_names_out()
            importance = self.model.feature_importances_
            
            # Get top features
            feature_importance = dict(zip(feature_names, importance))
            sorted_features = sorted(feature_importance.items(), 
                                   key=lambda x: x[1], reverse=True)
            
            return dict(sorted_features[:20])  # Top 20 features
            
        except Exception as e:
            self.logger.error(f"Error getting feature importance: {e}")
            return {}