"""
ArduPilot Documentation Retriever
Fetches and caches ArduPilot documentation for comprehensive parameter analysis
"""

import requests
import json
import time
import logging
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

class ArduPilotDocumentationRetriever:
    """Retrieves and caches ArduPilot documentation for telemetry parameters"""
    
    def __init__(self):
        self.base_url = "https://ardupilot.org/plane/docs/logmessages.html"
        self.documentation_cache = {}
        self.last_fetch = 0
        self.cache_duration = 3600  # 1 hour
        self._load_comprehensive_documentation()
    
    def _load_comprehensive_documentation(self):
        """Load comprehensive ArduPilot documentation"""
        try:
            # Load from cache if recent
            if time.time() - self.last_fetch < self.cache_duration:
                return
            
            # Fetch documentation from ArduPilot website
            response = requests.get(self.base_url, timeout=10)
            if response.status_code == 200:
                self._parse_documentation(response.text)
                self.last_fetch = time.time()
                logger.info("Successfully loaded ArduPilot documentation")
            else:
                logger.warning(f"Failed to fetch ArduPilot documentation: {response.status_code}")
                self._load_fallback_documentation()
                
        except Exception as e:
            logger.warning(f"Failed to load ArduPilot documentation: {e}")
            self._load_fallback_documentation()
    
    def _parse_documentation(self, html_content: str):
        """Parse HTML documentation to extract parameter information"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all message type sections
            message_sections = soup.find_all(['h2', 'h3', 'h4'], string=re.compile(r'^[A-Z]{2,4}$'))
            
            for section in message_sections:
                message_type = section.get_text().strip()
                self._extract_message_documentation(section, message_type)
                
        except Exception as e:
            logger.warning(f"Failed to parse ArduPilot documentation: {e}")
            self._load_fallback_documentation()
    
    def _extract_message_documentation(self, section, message_type: str):
        """Extract documentation for a specific message type"""
        try:
            # Find the next table or description
            next_element = section.find_next(['table', 'p', 'div'])
            
            if next_element and next_element.name == 'table':
                # Parse table for field information
                fields = self._parse_message_table(next_element)
                self.documentation_cache[message_type] = {
                    'type': message_type,
                    'description': self._get_message_description(section),
                    'fields': fields,
                    'source': 'ardupilot.org'
                }
            else:
                # Simple description
                self.documentation_cache[message_type] = {
                    'type': message_type,
                    'description': self._get_message_description(section),
                    'fields': {},
                    'source': 'ardupilot.org'
                }
                
        except Exception as e:
            logger.warning(f"Failed to extract documentation for {message_type}: {e}")
    
    def _parse_message_table(self, table) -> Dict[str, Dict[str, str]]:
        """Parse a message table to extract field information"""
        fields = {}
        try:
            rows = table.find_all('tr')
            headers = []
            
            # Get headers
            if rows:
                header_row = rows[0]
                headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]
            
            # Parse data rows
            for row in rows[1:]:
                cells = [td.get_text().strip() for td in row.find_all('td')]
                if len(cells) >= 2:
                    field_name = cells[0]
                    field_info = {}
                    
                    for i, header in enumerate(headers[1:], 1):
                        if i < len(cells):
                            field_info[header.lower().replace(' ', '_')] = cells[i]
                    
                    fields[field_name] = field_info
                    
        except Exception as e:
            logger.warning(f"Failed to parse message table: {e}")
            
        return fields
    
    def _get_message_description(self, section) -> str:
        """Get description for a message type"""
        try:
            # Look for description in next paragraph
            next_p = section.find_next('p')
            if next_p:
                return next_p.get_text().strip()
            
            # Look for description in parent or sibling elements
            parent = section.parent
            if parent:
                desc_elem = parent.find('p')
                if desc_elem:
                    return desc_elem.get_text().strip()
                    
        except Exception as e:
            logger.warning(f"Failed to get message description: {e}")
            
        return f"ArduPilot {section.get_text().strip()} message type"
    
    def _load_fallback_documentation(self):
        """Load fallback documentation when web fetch fails"""
        self.documentation_cache = {
            "GPS": {
                "type": "GPS",
                "description": "GPS position and velocity data",
                "fields": {
                    "Status": {"description": "GPS fix status", "units": "enum"},
                    "NSats": {"description": "Number of satellites", "units": "count"},
                    "HDop": {"description": "Horizontal dilution of precision", "units": "ratio"},
                    "VDop": {"description": "Vertical dilution of precision", "units": "ratio"},
                    "Lat": {"description": "Latitude", "units": "degrees"},
                    "Lng": {"description": "Longitude", "units": "degrees"},
                    "Alt": {"description": "Altitude", "units": "meters"},
                    "Spd": {"description": "Ground speed", "units": "m/s"},
                    "GCrs": {"description": "Ground course", "units": "degrees"}
                },
                "source": "fallback"
            },
            "GPA": {
                "type": "GPA",
                "description": "GPS accuracy information",
                "fields": {
                    "HAcc": {"description": "Horizontal accuracy", "units": "meters"},
                    "VAcc": {"description": "Vertical accuracy", "units": "meters"},
                    "SAcc": {"description": "Speed accuracy", "units": "m/s"},
                    "HDop": {"description": "Horizontal dilution of precision", "units": "ratio"},
                    "VDop": {"description": "Vertical dilution of precision", "units": "ratio"}
                },
                "source": "fallback"
            },
            "BAT": {
                "type": "BAT",
                "description": "Battery voltage and current",
                "fields": {
                    "Volt": {"description": "Battery voltage", "units": "volts"},
                    "Curr": {"description": "Battery current", "units": "amperes"},
                    "CurrTot": {"description": "Total current consumed", "units": "amperes"},
                    "Res": {"description": "Battery resistance", "units": "ohms"}
                },
                "source": "fallback"
            },
            "ATT": {
                "type": "ATT",
                "description": "Attitude data - roll, pitch, yaw angles",
                "fields": {
                    "Roll": {"description": "Roll angle", "units": "degrees"},
                    "Pitch": {"description": "Pitch angle", "units": "degrees"},
                    "Yaw": {"description": "Yaw angle", "units": "degrees"},
                    "DesRoll": {"description": "Desired roll angle", "units": "degrees"},
                    "DesPitch": {"description": "Desired pitch angle", "units": "degrees"},
                    "DesYaw": {"description": "Desired yaw angle", "units": "degrees"}
                },
                "source": "fallback"
            },
            "MODE": {
                "type": "MODE",
                "description": "Flight mode changes",
                "fields": {
                    "Mode": {"description": "Flight mode", "units": "enum"},
                    "Rsn": {"description": "Reason for mode change", "units": "enum"}
                },
                "source": "fallback"
            },
            "ERR": {
                "type": "ERR",
                "description": "Error and warning messages",
                "fields": {
                    "Subsys": {"description": "Subsystem", "units": "enum"},
                    "ECode": {"description": "Error code", "units": "enum"}
                },
                "source": "fallback"
            },
            "RCIN": {
                "type": "RCIN",
                "description": "RC input channels",
                "fields": {
                    "C1": {"description": "Channel 1", "units": "PWM"},
                    "C2": {"description": "Channel 2", "units": "PWM"},
                    "C3": {"description": "Channel 3", "units": "PWM"},
                    "C4": {"description": "Channel 4", "units": "PWM"},
                    "C5": {"description": "Channel 5", "units": "PWM"},
                    "C6": {"description": "Channel 6", "units": "PWM"},
                    "C7": {"description": "Channel 7", "units": "PWM"},
                    "C8": {"description": "Channel 8", "units": "PWM"}
                },
                "source": "fallback"
            },
            "RSSI": {
                "type": "RSSI",
                "description": "Radio signal strength indicator",
                "fields": {
                    "RSSI": {"description": "Signal strength", "units": "percentage"}
                },
                "source": "fallback"
            }
        }
        logger.info("Loaded fallback ArduPilot documentation")
    
    def get_parameter_documentation(self, parameter: str) -> Dict[str, Any]:
        """Get documentation for a specific parameter"""
        self._load_comprehensive_documentation()
        
        # Try exact match first
        if parameter in self.documentation_cache:
            return self.documentation_cache[parameter]
        
        # Try case-insensitive match
        for key, value in self.documentation_cache.items():
            if key.upper() == parameter.upper():
                return value
        
        # Try partial match
        for key, value in self.documentation_cache.items():
            if parameter.upper() in key.upper() or key.upper() in parameter.upper():
                return value
        
        # Return default documentation
        return {
            "type": parameter,
            "description": f"ArduPilot {parameter} parameter - documentation not available",
            "fields": {},
            "source": "default"
        }
    
    def get_field_documentation(self, message_type: str, field_name: str) -> Dict[str, str]:
        """Get documentation for a specific field within a message type"""
        message_doc = self.get_parameter_documentation(message_type)
        
        if field_name in message_doc.get("fields", {}):
            return message_doc["fields"][field_name]
        
        # Try case-insensitive match
        for field, doc in message_doc.get("fields", {}).items():
            if field.upper() == field_name.upper():
                return doc
        
        return {
            "description": f"{field_name} field in {message_type} message",
            "units": "unknown"
        }
    
    def get_all_parameters(self) -> List[str]:
        """Get list of all available parameters"""
        self._load_comprehensive_documentation()
        return list(self.documentation_cache.keys())
    
    def search_parameters(self, query: str) -> List[Dict[str, Any]]:
        """Search for parameters matching a query"""
        self._load_comprehensive_documentation()
        results = []
        query_lower = query.lower()
        
        for param, doc in self.documentation_cache.items():
            if (query_lower in param.lower() or 
                query_lower in doc.get("description", "").lower()):
                results.append({
                    "parameter": param,
                    "description": doc.get("description", ""),
                    "fields": list(doc.get("fields", {}).keys())
                })
        
        return results

# Global instance
_global_docs_retriever = None

def get_global_docs_retriever() -> ArduPilotDocumentationRetriever:
    """Get global ArduPilot documentation retriever instance"""
    global _global_docs_retriever
    if _global_docs_retriever is None:
        _global_docs_retriever = ArduPilotDocumentationRetriever()
    return _global_docs_retriever
