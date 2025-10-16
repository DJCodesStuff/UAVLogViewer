import { mavlink20 as mavlink } from '../libs/mavlink'
import { ParamSeeker } from '../tools/paramseeker'

const validGCSs = [
    mavlink.MAV_TYPE_FIXED_WING,
    mavlink.MAV_TYPE_QUADROTOR,
    mavlink.MAV_TYPE_COAXIAL,
    mavlink.MAV_TYPE_HELICOPTER,
    mavlink.MAV_TYPE_ANTENNA_TRACKER,
    mavlink.MAV_TYPE_AIRSHIP,
    mavlink.MAV_TYPE_FREE_BALLOON,
    mavlink.MAV_TYPE_ROCKET,
    mavlink.MAV_TYPE_GROUND_ROVER,
    mavlink.MAV_TYPE_SURFACE_BOAT,
    mavlink.MAV_TYPE_SUBMARINE,
    mavlink.MAV_TYPE_HEXAROTOR,
    mavlink.MAV_TYPE_OCTOROTOR,
    mavlink.MAV_TYPE_TRICOPTER,
    mavlink.MAV_TYPE_FLAPPING_WING,
    mavlink.MAV_TYPE_KITE
]

export class MavlinkDataExtractor {
    static extractAttitude (messages, source) {
        const attitudes = {}
        if ('ATTITUDE' in messages) {
            const attitudeMsgs = messages.ATTITUDE
            for (const i in attitudeMsgs.time_boot_ms) {
                attitudes[parseInt(attitudeMsgs.time_boot_ms[i])] =
                    [
                        attitudeMsgs.roll[i],
                        attitudeMsgs.pitch[i],
                        attitudeMsgs.yaw[i]
                    ]
            }
        }
        return attitudes
    }

    static extractAttitudeQ (messages, source) {
        return {}
    }

    static extractFlightModes (messages) {
        let modes = []
        if ('HEARTBEAT' in messages) {
            const msgs = messages.HEARTBEAT
            modes = [[msgs.time_boot_ms[0], msgs.asText[0]]]
            for (const i in msgs.time_boot_ms) {
                if (validGCSs.includes(msgs.type[i])) {
                    if (msgs.asText[i] === undefined) {
                        msgs.asText[i] = 'Unknown'
                    }
                    if (msgs.asText[i] !== null && msgs.asText[i] !== modes[modes.length - 1][1]) {
                        modes.push([msgs.time_boot_ms[i], msgs.asText[i]])
                    }
                }
            }
        }
        return modes
    }

    static extractEvents (messages) {
        let armedState = []
        if ('HEARTBEAT' in messages) {
            const msgs = messages.HEARTBEAT
            const event = (msgs.base_mode[0] & 0b10000000) === 128 ? 'Armed' : 'Disarmed'
            armedState = [[msgs.time_boot_ms[0], event]]
            for (const i in msgs.time_boot_ms) {
                if (msgs.type[i] !== mavlink.MAV_TYPE_GCS) {
                    const newEvent = (msgs.base_mode[i] & 0b10000000) === 128 ? 'Armed' : 'Disarmed'
                    if (newEvent !== armedState[armedState.length - 1][1]) {
                        const event = (msgs.base_mode[i] & 0b10000000) === 128 ? 'Armed' : 'Disarmed'
                        armedState.push([msgs.time_boot_ms[i], event])
                    }
                }
            }
        }
        return armedState
    }

    static extractMission (messages) {
        const wps = []
        if ('CMD' in messages) {
            const cmdMsgs = messages.CMD
            for (const i in cmdMsgs.time_boot_ms) {
                if (cmdMsgs.Lat[i] !== 0) {
                    let lat = cmdMsgs.Lat[i]
                    let lon = cmdMsgs.Lng[[i]]
                    if (Math.abs(lat) > 180) {
                        lat = lat / 10e6
                        lon = lon / 10e6
                    }
                    wps.push([lon, lat, cmdMsgs.Alt[i]])
                }
            }
        }
        return wps
    }

    static extractFences (messages) {
        return []
    }

    static extractVehicleType (messages) {
        if ('HEARTBEAT' in messages) {
            for (const i in messages.HEARTBEAT.craft) {
                if (messages.HEARTBEAT.craft[i] !== undefined) {
                    return messages.HEARTBEAT.craft[i]
                }
            }
        }
    }

    static extractAttitudeSources (messages) {
        return {
            quaternions: [],
            eulers: ['ATTITUDE']
        }
    }

    static extractTrajectorySources (messages) {
        const sources = []
        if ('GLOBAL_POSITION_INT' in messages) {
            sources.push('GLOBAL_POSITION_INT')
        }
        if ('GPS_RAW_INT' in messages) {
            sources.push('GPS_RAW_INT')
        }
        if ('AHRS2' in messages) {
            sources.push('AHRS2')
        }
        if ('AHRS3' in messages) {
            sources.push('AHRS3')
        }
        return sources
    }

    static extractTrajectory (messages, source) {
        const ret = {}
        if (('GLOBAL_POSITION_INT' in messages) && source === 'GLOBAL_POSITION_INT') {
            const trajectory = []
            const timeTrajectory = {}
            let startAltitude = null
            const gpsData = messages.GLOBAL_POSITION_INT
            for (const i in gpsData.time_boot_ms) {
                if (gpsData.lat[i] !== 0) {
                    if (startAltitude === null) {
                        startAltitude = gpsData.relative_alt[i]
                    }
                    trajectory.push(
                        [
                            gpsData.lon[i],
                            gpsData.lat[i],
                            gpsData.relative_alt[i] - startAltitude,
                            gpsData.time_boot_ms[i]
                        ]
                    )
                    timeTrajectory[gpsData.time_boot_ms[i]] = [
                        gpsData.lon[i],
                        gpsData.lat[i],
                        gpsData.relative_alt[i],
                        gpsData.time_boot_ms[i]]
                }
            }
            if (trajectory.length) {
                ret.GLOBAL_POSITION_INT = {
                    startAltitude: startAltitude,
                    trajectory: trajectory,
                    timeTrajectory: timeTrajectory
                }
            }
        }
        if ('GPS_RAW_INT' in messages && source === 'GPS_RAW_INT') {
            const trajectory = []
            const timeTrajectory = {}
            let startAltitude = null
            const gpsData = messages.GPS_RAW_INT
            for (const i in gpsData.time_boot_ms) {
                if (gpsData.lat[i] !== 0) {
                    if (startAltitude === null) {
                        startAltitude = gpsData.alt[0] / 1000
                    }
                    trajectory.push(
                        [
                            gpsData.lon[i] * 1e-7,
                            gpsData.lat[i] * 1e-7,
                            gpsData.alt[i] / 1000 - startAltitude,
                            gpsData.time_boot_ms[i]
                        ]
                    )
                    timeTrajectory[gpsData.time_boot_ms[i]] = [
                        gpsData.lon[i] * 1e-7,
                        gpsData.lat[i] * 1e-7,
                        gpsData.alt[i] / 1000,
                        gpsData.time_boot_ms[i]]
                }
            }
            if (trajectory.length) {
                ret.GPS_RAW_INT = {
                    startAltitude: startAltitude,
                    trajectory: trajectory,
                    timeTrajectory: timeTrajectory
                }
            }
        }
        if ('AHRS2' in messages && source === 'AHRS2') {
            const trajectory = []
            const timeTrajectory = {}
            let startAltitude = null
            const gpsData = messages.AHRS2
            for (const i in gpsData.time_boot_ms) {
                if (startAltitude === null) {
                    startAltitude = gpsData.altitude[0]
                }
                trajectory.push(
                    [
                        gpsData.lng[i] * 1e-7,
                        gpsData.lat[i] * 1e-7,
                        gpsData.altitude[i] - startAltitude,
                        gpsData.time_boot_ms[i]
                    ]
                )
                timeTrajectory[gpsData.time_boot_ms[i]] = [
                    gpsData.lng[i] * 1e-7,
                    gpsData.lat[i] * 1e-7,
                    gpsData.altitude[i],
                    gpsData.time_boot_ms[i]]
            }
            if (trajectory.length) {
                ret.AHRS2 = {
                    startAltitude: startAltitude,
                    trajectory: trajectory,
                    timeTrajectory: timeTrajectory
                }
            }
        }
        if ('AHRS3' in messages && source === 'AHRS3') {
            const trajectory = []
            const timeTrajectory = {}
            let startAltitude = null
            const gpsData = messages.AHRS3
            for (const i in gpsData.time_boot_ms) {
                if (gpsData.lat[i] !== 0) {
                    if (startAltitude === null) {
                        startAltitude = gpsData.altitude[0]
                    }
                    trajectory.push(
                        [
                            gpsData.lng[i] * 1e-7,
                            gpsData.lat[i] * 1e-7,
                            gpsData.altitude[i] - startAltitude,
                            gpsData.time_boot_ms[i]
                        ]
                    )
                    timeTrajectory[gpsData.time_boot_ms[i]] = [
                        gpsData.lng[i] * 1e-7,
                        gpsData.lat[i] * 1e-7,
                        gpsData.altitude[i],
                        gpsData.time_boot_ms[i]]
                }
            }
            if (trajectory.length) {
                ret.AHRS3 = {
                    startAltitude: startAltitude,
                    trajectory: trajectory,
                    timeTrajectory: timeTrajectory
                }
            }
        }
        return ret
    }

    static extractDefaultParams (messages) {
        return {}
    }

    static extractParams (messages) {
        const params = []
        const lastValue = {}
        if ('PARAM_VALUE' in messages) {
            const paramData = messages.PARAM_VALUE
            for (const i in paramData.time_boot_ms) {
                const paramName = paramData.param_id[i].replace(/[^a-z0-9A-Z_]/ig, '')
                const paramValue = paramData.param_value[i]
                if (lastValue.paramName && lastValue[paramName] === paramValue) {
                    continue
                }
                params.push(
                    [
                        paramData.time_boot_ms[i],
                        paramName,
                        paramValue
                    ]
                )
                lastValue[paramName] = paramValue
            }
        }
        if (params.length > 0) {
            return new ParamSeeker(params)
        } else {
            return undefined
        }
    }

    static extractTextMessages (messages) {
        const texts = []
        if ('STATUSTEXT' in messages) {
            const textMsgs = messages.STATUSTEXT
            for (const i in textMsgs.time_boot_ms) {
                texts.push([textMsgs.time_boot_ms[i], textMsgs.severity[i], textMsgs.text[i]])
            }
        }
        return texts
    }

    static extractNamedValueFloatNames (messages) {
        if ('NAMED_VALUE_FLOAT' in messages) {
            return Array.from(new Set(messages.NAMED_VALUE_FLOAT.name))
        }
        return []
    }

    static extractStartTime (messages) {
        return undefined
    }

    static extractGpsHealth (messages) {
        /* eslint-disable camelcase */
        const gpsHealth = {
            'status_changes': [],
            'satellite_counts': [],
            'signal_quality': [],
            'accuracy_metrics': []
        }

        // Prefer GPS_RAW_INT as primary time series source
        if ('GPS_RAW_INT' in messages) {
            const gps = messages.GPS_RAW_INT
            // Build status changes based on fix_type transitions
            const fixName = (ft) => {
                const map = {
                    0: 'NO_GPS',
                    1: 'NO_FIX',
                    2: '2D_FIX',
                    3: '3D_FIX',
                    4: 'DGPS',
                    5: 'RTK_FLOAT',
                    6: 'RTK_FIXED',
                    7: 'STATIC',
                    8: 'PPP'
                }
                return map[ft] || String(ft)
            }
            let lastFix = null
            for (const i in gps.time_boot_ms) {
                const t = gps.time_boot_ms[i]
                // Satellites
                if (gps['satellites_visible'] && gps['satellites_visible'][i] !== undefined) {
                    gpsHealth['satellite_counts'].push(parseInt(gps['satellites_visible'][i]))
                }
                // Signal quality (HDOP/VDOP where available as eph/epv)
                if (gps.eph && gps.eph[i] !== undefined) {
                    const entry = { timestamp: t, hdop: parseFloat(gps.eph[i]) }
                    if (gps.epv && gps.epv[i] !== undefined) {
                        entry.vdop = parseFloat(gps.epv[i])
                    }
                    gpsHealth['signal_quality'].push(entry)
                }
                // Accuracy metrics (h_acc/v_acc if present)
                const hasHAcc = gps['h_acc'] && gps['h_acc'][i] !== undefined
                const hasVAcc = gps['v_acc'] && gps['v_acc'][i] !== undefined
                if (hasHAcc || hasVAcc) {
                    gpsHealth['accuracy_metrics'].push({
                        timestamp: t,
                        hacc: hasHAcc ? parseFloat(gps['h_acc'][i]) : undefined,
                        vacc: hasVAcc ? parseFloat(gps['v_acc'][i]) : undefined
                    })
                }
                // Fix type transitions
                if (gps['fix_type'] && gps['fix_type'][i] !== undefined) {
                    const curr = parseInt(gps['fix_type'][i])
                    if (lastFix === null || curr !== lastFix) {
                        gpsHealth['status_changes'].push({ timestamp: t, status: fixName(curr), 'fix_type': curr })
                        lastFix = curr
                    }
                }
            }
        }

        // GPS_STATUS may provide satellite visibility snapshots without timestamps
        if ('GPS_STATUS' in messages && gpsHealth['satellite_counts'].length === 0) {
            const status = messages.GPS_STATUS
            if (status.satellites_visible && status.satellites_visible.length) {
                for (const i in status.satellites_visible) {
                    gpsHealth['satellite_counts'].push(parseInt(status.satellites_visible[i]))
                }
            }
        }

        /* eslint-enable camelcase */
        return gpsHealth
    }

    static extractBatterySeries (messages) {
        const series = []
        // SYS_STATUS: voltage_battery (mV), current_battery (cA), battery_remaining (%)
        if ('SYS_STATUS' in messages) {
            const m = messages.SYS_STATUS
            for (const i in m.time_boot_ms) {
                const ts = m.time_boot_ms[i]
                const v = m.voltage_battery ? m.voltage_battery[i] : undefined // mV
                const c = m.current_battery ? m.current_battery[i] : undefined // cA
                const rem = m.battery_remaining ? m.battery_remaining[i] : undefined // %
                series.push({
                    timestamp: ts,
                    voltage: (typeof v === 'number') ? v / 1000.0 : undefined,
                    current: (typeof c === 'number') ? c / 100.0 : undefined,
                    remaining: rem
                })
            }
        }
        // BATTERY_STATUS (optional)
        if ('BATTERY_STATUS' in messages) {
            const b = messages.BATTERY_STATUS
            for (const i in b.time_boot_ms) {
                const ts = b.time_boot_ms[i]
                const temp = b.temperature ? b.temperature[i] : undefined // cdegC
                const cur = b.current_battery ? b.current_battery[i] : undefined // cA
                const voltArray = b.voltages ? b.voltages[i] : null // per-cell mV array
                let totalV
                if (Array.isArray(voltArray)) {
                    totalV = voltArray.reduce((a, v) => a + (typeof v === 'number' ? v : 0), 0)
                }
                series.push({
                    timestamp: ts,
                    voltage: (typeof totalV === 'number' && totalV > 0) ? totalV / 1000.0 : undefined,
                    current: (typeof cur === 'number') ? cur / 100.0 : undefined,
                    temperature: (typeof temp === 'number') ? temp / 100.0 : undefined
                })
            }
        }
        // Additional temperature sources (best-effort): SCALED_PRESSURE temperature (air), NAMED_VALUE_FLOAT
        if ('SCALED_PRESSURE' in messages) {
            const sp = messages.SCALED_PRESSURE
            for (const i in sp.time_boot_ms) {
                const ts = sp.time_boot_ms[i]
                const tempC = (typeof sp.temperature?.[i] === 'number') ? sp.temperature[i] / 100.0 : undefined
                if (tempC !== undefined) {
                    series.push({ timestamp: ts, temperature: tempC })
                }
            }
        }
        if ('NAMED_VALUE_FLOAT' in messages) {
            const nvf = messages.NAMED_VALUE_FLOAT
            if (Array.isArray(nvf.time_boot_ms) && Array.isArray(nvf.name) && Array.isArray(nvf.value)) {
                for (const i in nvf.time_boot_ms) {
                    const name = String(nvf.name[i] || '').toUpperCase()
                    // Heuristic: only pick likely battery temps
                    if (name.includes('BATT') && name.includes('TEMP')) {
                        series.push({ timestamp: nvf.time_boot_ms[i], temperature: nvf.value[i] })
                    }
                }
            }
        }
        return series
    }
}
