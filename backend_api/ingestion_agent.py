import json
import os
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class DataIngestionAgent:
    """Builds structured, LLM-friendly summaries and indexes them into per-session Qdrant."""

    def __init__(self, gemini_service, qdrant_service, telemetry_service):
        self.gemini = gemini_service
        self.qdrant = qdrant_service
        self.telemetry = telemetry_service

    def _time_meta(self, timestamps: List[float]) -> Dict[str, Any]:
        if not timestamps:
            return {'start': None, 'end': None, 'duration_s': None}
        t0, t1 = min(timestamps), max(timestamps)
        return {'start': t0, 'end': t1, 'duration_s': round(t1 - t0, 3)}

    def _stream_card(self, name: str, data: Dict[str, Any], units: Dict[str, str]) -> Dict[str, Any]:
        timestamps: List[float] = []
        if name == 'GPS':
            timestamps = [p.get('timestamp') for p in data.get('data', []) if isinstance(p, dict)]
        elif name == 'ALTITUDE':
            timestamps = [p[0] for p in data.get('data', []) if isinstance(p, (list, tuple)) and len(p) >= 2]
        elif name == 'BATTERY':
            timestamps = [p.get('timestamp') for p in data.get('data', []) if isinstance(p, dict)]
        elif name in ('ATTITUDE', 'ROLL', 'PITCH', 'YAW'):
            timestamps = [p.get('timestamp') for p in data.get('data', []) if isinstance(p, dict)]

        card = {
            'type': 'stream_card',
            'stream': name,
            'count': data.get('count', 0),
            'statistics': data.get('statistics', {}),
            'units': units,
            'time': self._time_meta([t for t in timestamps if isinstance(t, (int, float))]),
            'sample_preview': data.get('data', [])[:10]
        }
        if isinstance(data.get('metadata'), dict):
            card['metadata'] = data['metadata']
        return card

    # -------------------- Derived cards (overview/quality/issues/anomalies) --------------------
    def _compute_flight_overview(self, session_id: str, flight_data: Dict[str, Any]) -> Dict[str, Any]:
        """Flight-level overview with total duration and stream availability."""
        try:
            session_meta = {
                'vehicle_type': flight_data.get('vehicle', 'Unknown'),
                'log_type': flight_data.get('logType', 'Unknown'),
                'metadata': flight_data.get('metadata', {})
            }
            # Prefer explicit duration in metadata, else derive from streams
            duration = None
            md = flight_data.get('metadata') or {}
            if isinstance(md.get('duration'), (int, float)):
                duration = float(md['duration'])
            else:
                # derive from GPS/ALT timestamps
                gps = self.telemetry.get_parameter_data(session_id, 'GPS')
                alt = self.telemetry.get_parameter_data(session_id, 'ALTITUDE')
                gps_ts = [p.get('timestamp') for p in gps.get('data', []) if isinstance(p, dict)]
                alt_ts = [t for (t, _) in alt.get('data', [])]
                def _range(ts: List[float]):
                    ts = [t for t in ts if isinstance(t, (int, float))]
                    return (max(ts) - min(ts)) if ts else None
                candidates = [r for r in (_range(gps_ts), _range(alt_ts)) if isinstance(r, (int, float))]
                duration = max(candidates) if candidates else None
            availability = {
                'has_gps': bool(flight_data.get('trajectories')),
                'has_battery': bool(flight_data.get('batterySeries') or flight_data.get('battery_series')),
                'has_attitude': bool(flight_data.get('timeAttitude')),
                'has_events': bool(flight_data.get('events')),
                'has_flight_modes': bool(flight_data.get('flightModeChanges')),
                'has_gps_metadata': bool(flight_data.get('gps_metadata'))
            }
            return {
                'type': 'flight_overview',
                'session_id': session_id,
                'vehicle_type': session_meta['vehicle_type'],
                'log_type': session_meta['log_type'],
                'duration_s': round(duration, 3) if isinstance(duration, (int, float)) else None,
                'availability': availability
            }
        except Exception as e:
            logger.error(f"flight_overview error: {e}")
            return {'type': 'flight_overview', 'session_id': session_id}

    def _compute_data_quality(self, session_id: str, flight_data: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate sampling rate and missingness per stream for quick QA."""
        try:
            meta = self.telemetry.build_session_metadata(session_id, flight_data)
            streams = meta.get('streams', {}) if isinstance(meta, dict) else {}
            quality = {}
            for key, info in streams.items():
                if not isinstance(info, dict):
                    continue
                quality[key] = {
                    'sampling_hz': info.get('sampling_hz'),
                    'missing_ratio': info.get('missing_ratio'),
                    'duration_s': (info.get('time_range') or {}).get('duration_s') if isinstance(info.get('time_range'), dict) else None
                }
            return {
                'type': 'data_quality_overview',
                'session_id': session_id,
                'quality': quality
            }
        except Exception as e:
            logger.error(f"data_quality_overview error: {e}")
            return {'type': 'data_quality_overview', 'session_id': session_id}

    def _compute_gps_issues(self, session_id: str, flight_data: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize potential GPS issues based on quality and events without LLM."""
        try:
            quality = self.telemetry._extract_gps_quality(flight_data) or {}
            events = self.telemetry._extract_events(flight_data, None)
            gps_events = []
            for e in events.get('data', []) if isinstance(events, dict) else []:
                if isinstance(e, dict):
                    typ = (e.get('type') or '').upper()
                    msg = (e.get('message') or '').upper()
                    if 'GPS' in typ or 'GPS' in msg:
                        gps_events.append({'timestamp': e.get('timestamp'), 'type': e.get('type'), 'message': e.get('message'), 'severity': e.get('severity')})
            hacc_stats = None
            if isinstance(quality.get('accuracy'), dict) and isinstance(quality['accuracy'].get('hacc'), dict):
                hacc_stats = quality['accuracy']['hacc']
            latest_status = quality.get('latest_status')
            statuses = quality.get('statuses') if isinstance(quality.get('statuses'), list) else None
            return {
                'type': 'gps_issues_overview',
                'session_id': session_id,
                'latest_status': latest_status,
                'status_changes': statuses,
                'hacc_stats': hacc_stats,
                'gps_events': gps_events[:10]
            }
        except Exception as e:
            logger.error(f"gps_issues_overview error: {e}")
            return {'type': 'gps_issues_overview', 'session_id': session_id}

    def _compute_anomalies_overview(self, session_id: str, flight_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run anomaly detection (LLM-backed) and summarize results for quick retrieval."""
        try:
            anomalies = self.telemetry.detect_anomalies(session_id)
            summary = {
                'total': len(anomalies),
                'by_severity': {},
                'examples': anomalies[:5]
            }
            for a in anomalies:
                if isinstance(a, dict):
                    sev = (a.get('severity') or 'unknown').lower()
                    summary['by_severity'][sev] = summary['by_severity'].get(sev, 0) + 1
            return {
                'type': 'anomalies_overview',
                'session_id': session_id,
                'summary': summary
            }
        except Exception as e:
            logger.error(f"anomalies_overview error: {e}")
            return {'type': 'anomalies_overview', 'session_id': session_id}

    def _build_structured_docs(self, session_id: str, flight_data: Dict[str, Any]) -> Tuple[List[str], List[Dict[str, Any]]]:
        texts: List[str] = []
        payloads: List[Dict[str, Any]] = []

        session_meta = {
            'type': 'session_meta',
            'session_id': session_id,
            'vehicle_type': flight_data.get('vehicle', 'Unknown'),
            'log_type': flight_data.get('logType', 'Unknown'),
            'metadata': flight_data.get('metadata', {}),
            'availability': {
                'has_gps': bool(flight_data.get('trajectories')),
                'has_battery': bool(flight_data.get('batterySeries') or flight_data.get('battery_series')),
                'has_attitude': bool(flight_data.get('timeAttitude')),
                'has_events': bool(flight_data.get('events')),
                'has_flight_modes': bool(flight_data.get('flightModeChanges')),
                'has_gps_metadata': bool(flight_data.get('gps_metadata'))
            }
        }
        text = json.dumps(session_meta, ensure_ascii=False)
        texts.append(text)
        payloads.append({'type': 'session_meta', 'session_id': session_id, 'text': text})

        # GPS + ALTITUDE
        if flight_data.get('trajectories'):
            gps = self.telemetry.get_parameter_data(session_id, 'GPS')
            texts.append(json.dumps(self._stream_card('GPS', gps, {
                'longitude': 'deg', 'latitude': 'deg', 'altitude': 'm', 'timestamp': 's'
            }), ensure_ascii=False))
            payloads.append({'type': 'stream_stats', 'stream': 'gps', 'session_id': session_id, 'text': texts[-1]})

            alt = self.telemetry.get_parameter_data(session_id, 'ALTITUDE')
            texts.append(json.dumps(self._stream_card('ALTITUDE', alt, {
                'altitude': 'm', 'timestamp': 's'
            }), ensure_ascii=False))
            payloads.append({'type': 'stream_stats', 'stream': 'altitude', 'session_id': session_id, 'text': texts[-1]})

        # BATTERY
        if flight_data.get('batterySeries') or flight_data.get('battery_series'):
            bat = self.telemetry.get_parameter_data(session_id, 'BATTERY')
            texts.append(json.dumps(self._stream_card('BATTERY', bat, {
                'voltage': 'V', 'current': 'A', 'remaining': '%', 'temperature': 'C', 'timestamp': 's'
            }), ensure_ascii=False))
            payloads.append({'type': 'stream_stats', 'stream': 'battery', 'session_id': session_id, 'text': texts[-1]})

        # ATTITUDE
        if flight_data.get('timeAttitude'):
            att = self.telemetry.get_parameter_data(session_id, 'ATTITUDE')
            texts.append(json.dumps(self._stream_card('ATTITUDE', att, {
                'roll': 'deg', 'pitch': 'deg', 'yaw': 'deg', 'timestamp': 's'
            }), ensure_ascii=False))
            payloads.append({'type': 'stream_stats', 'stream': 'attitude', 'session_id': session_id, 'text': texts[-1]})

        # EVENTS overview
        if flight_data.get('events'):
            ev = self.telemetry.get_parameter_data(session_id, 'EVENTS')
            ev_doc = {
                'type': 'events_overview', 'session_id': session_id,
                'count': ev.get('count', 0),
                'first_10': ev.get('data', [])[:10]
            }
            text = json.dumps(ev_doc, ensure_ascii=False)
            texts.append(text)
            payloads.append({'type': 'events_overview', 'session_id': session_id, 'text': text})

        # GPS QUALITY
        if flight_data.get('gps_metadata'):
            gpsq = self.telemetry.get_parameter_data(session_id, 'GPS_QUALITY')
            gpsq_doc = {'type': 'gps_quality_overview', 'session_id': session_id, 'quality': gpsq}
            text = json.dumps(gpsq_doc, ensure_ascii=False)
            texts.append(text)
            payloads.append({'type': 'gps_quality', 'session_id': session_id, 'text': text})

        # Derived: flight overview (duration, availability)
        try:
            flight_overview = self._compute_flight_overview(session_id, flight_data)
            texts.append(json.dumps(flight_overview, ensure_ascii=False))
            payloads.append({'type': 'flight_overview', 'session_id': session_id, 'text': texts[-1]})
        except Exception as e:
            logger.error(f"build flight_overview failed: {e}")

        # Derived: data quality overview
        try:
            dq = self._compute_data_quality(session_id, flight_data)
            texts.append(json.dumps(dq, ensure_ascii=False))
            payloads.append({'type': 'data_quality_overview', 'session_id': session_id, 'text': texts[-1]})
        except Exception as e:
            logger.error(f"build data_quality_overview failed: {e}")

        # Derived: gps issues overview
        try:
            gi = self._compute_gps_issues(session_id, flight_data)
            texts.append(json.dumps(gi, ensure_ascii=False))
            payloads.append({'type': 'gps_issues_overview', 'session_id': session_id, 'text': texts[-1]})
        except Exception as e:
            logger.error(f"build gps_issues_overview failed: {e}")

        # Derived: anomalies overview (LLM-backed)
        try:
            ao = self._compute_anomalies_overview(session_id, flight_data)
            texts.append(json.dumps(ao, ensure_ascii=False))
            payloads.append({'type': 'anomalies_overview', 'session_id': session_id, 'text': texts[-1]})
        except Exception as e:
            logger.error(f"build anomalies_overview failed: {e}")

        return texts, payloads

    def ingest_session(self, session_id: str, flight_data: Dict[str, Any]) -> bool:
        """Create structured docs and index them into the per-session collection."""
        try:
            collection = f"session_{session_id}"
            self.qdrant.ensure_collection(collection)

            texts, payloads = self._build_structured_docs(session_id, flight_data)
            if not texts:
                logger.info("No docs to ingest for session %s", session_id)
                return False

            # Dump structured docs to rag_docs for inspection
            try:
                project_root = os.path.dirname(os.path.dirname(__file__))
                dump_dir = os.path.join(project_root, 'rag_docs', f'session_{session_id}')
                os.makedirs(dump_dir, exist_ok=True)

                def _fname_for_payload(pl: Dict[str, Any], i: int) -> str:
                    ptype = pl.get('type')
                    if ptype == 'session_meta':
                        return '900_session_meta.json'
                    if ptype == 'stream_stats':
                        stream = (pl.get('stream') or 'stream').lower()
                        order = {
                            'gps': 901,
                            'altitude': 902,
                            'battery': 903,
                            'attitude': 904,
                        }
                        base = order.get(stream, 905 + i)
                        return f"{base:03d}_stream_{stream}.json"
                    if ptype == 'events_overview':
                        return '910_events_overview.json'
                    if ptype == 'gps_quality':
                        return '920_gps_quality.json'
                    if ptype == 'flight_overview':
                        return '930_flight_overview.json'
                    if ptype == 'data_quality_overview':
                        return '931_data_quality_overview.json'
                    if ptype == 'gps_issues_overview':
                        return '932_gps_issues_overview.json'
                    if ptype == 'anomalies_overview':
                        return '933_anomalies_overview.json'
                    return f"999_structured_{i}.json"

                for i, (text, pl) in enumerate(zip(texts, payloads)):
                    try:
                        fname = _fname_for_payload(pl, i)
                        with open(os.path.join(dump_dir, fname), 'w', encoding='utf-8') as f:
                            f.write(text if isinstance(text, str) else str(text))
                    except Exception as e:
                        logger.error(f"Error writing structured dump {i}: {e}")

                # Structured manifest
                try:
                    manifest_path = os.path.join(dump_dir, 'structured_manifest.json')
                    with open(manifest_path, 'w', encoding='utf-8') as mf:
                        json.dump({'session_id': session_id, 'count': len(texts), 'payloads': payloads}, mf, ensure_ascii=False, indent=2)
                except Exception as e:
                    logger.error(f"Error writing structured manifest: {e}")
            except Exception as e:
                logger.error(f"Error dumping structured docs to rag_docs: {e}")

            vectors = self.gemini.embed_texts(texts)
            if not vectors or len(vectors) != len(texts):
                logger.warning("Skipping upsert: missing embeddings or count mismatch")
                return False

            ok = self.qdrant.add_documents_to_collection(collection, payloads, vectors)
            logger.info("Ingestion indexed %d docs into %s", len(texts), collection)
            return bool(ok)
        except Exception as e:
            logger.error("Ingestion error for session %s: %s", session_id, e)
            return False


