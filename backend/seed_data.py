import json
from sqlalchemy.orm import Session
from models import Concept, ConceptPrerequisite, Question

# ----------------------------------------------------------------------------
# 9 CONCEPTS (Class 10 Physics - Electricity)
# ----------------------------------------------------------------------------
CONCEPTS_DATA = [
    {
        "id": "electric-current",
        "title": "Electric Current",
        "description": "Rate of flow of electric charge: I = Q/t, measured in Amperes (Coulombs per second). Direction of conventional current versus electron flow.",
        "category": "Electricity",
        "order_index": 1
    },
    {
        "id": "potential-difference",
        "title": "Potential Difference",
        "description": "Work done in moving a unit positive charge between two points: V = W/Q, measured in Volts. Role of electric potential in driving current.",
        "category": "Electricity",
        "order_index": 2
    },
    {
        "id": "resistance",
        "title": "Resistance",
        "description": "Property of a conductor by virtue of which it opposes the flow of electric current through it. Measured in Ohms (Ω).",
        "category": "Electricity",
        "order_index": 3
    },
    {
        "id": "factors-affecting-resistance",
        "title": "Factors Affecting Resistance",
        "description": "Dependence of resistance on length, cross-sectional area, material resistivity (R = ρL/A), and temperature.",
        "category": "Electricity",
        "order_index": 4
    },
    {
        "id": "ohms-law",
        "title": "Ohm's Law",
        "description": "Direct linear proportionality between potential difference and current at constant temperature: V = IR.",
        "category": "Electricity",
        "order_index": 5
    },
    {
        "id": "series-circuits",
        "title": "Series Circuits",
        "description": "Single-loop circuit configuration where current is constant throughout, total resistance adds linearly (Req = R1 + R2), and voltage divides.",
        "category": "Electricity",
        "order_index": 6
    },
    {
        "id": "parallel-circuits",
        "title": "Parallel Circuits",
        "description": "Multiple independent branching paths where potential difference is identical across branches, current divides, and 1/Req = 1/R1 + 1/R2.",
        "category": "Electricity",
        "order_index": 7
    },
    {
        "id": "electrical-power",
        "title": "Electrical Power",
        "description": "Rate at which electrical energy is consumed or dissipated: P = VI = I^2R = V^2/R, measured in Watts (W) and Kilowatt-hours (kWh).",
        "category": "Electricity",
        "order_index": 8
    },
    {
        "id": "heating-effect",
        "title": "Heating Effect of Electric Current",
        "description": "Joule's Law of Heating: heat produced in a resistor is proportional to square of current, resistance, and time (H = I^2Rt). Practical applications in appliances and fuses.",
        "category": "Electricity",
        "order_index": 9
    }
]

# ----------------------------------------------------------------------------
# PREREQUISITE EDGES (Directed Acyclic Graph)
# ----------------------------------------------------------------------------
PREREQUISITES_DATA = [
    ("electric-current", "ohms-law"),
    ("potential-difference", "ohms-law"),
    ("factors-affecting-resistance", "resistance"),
    ("resistance", "ohms-law"),
    ("ohms-law", "series-circuits"),
    ("ohms-law", "parallel-circuits"),
    ("ohms-law", "electrical-power"),
    ("series-circuits", "electrical-power"),
    ("parallel-circuits", "electrical-power"),
    ("electrical-power", "heating-effect")
]

# ----------------------------------------------------------------------------
# 27+ HIGH-QUALITY QUESTIONS COVERING ALL 9 CONCEPTS & DIFFICULTIES
# ----------------------------------------------------------------------------
QUESTIONS_DATA = [
    # 1. Electric Current (3 questions)
    {
        "concept_id": "electric-current",
        "prompt": "What defines electric current in a metallic conductor?",
        "difficulty": 1,
        "question_type": "conceptual",
        "options": ["Rate of flow of electric charge per unit time", "Total electrical energy stored in a cell", "Speed of electrons through the vacuum", "Opposition offered to moving charges"],
        "correct_answer": "Rate of flow of electric charge per unit time",
        "explanation": "Electric current is defined as the net quantity of electric charge passing through any cross-section of a conductor per unit time: I = Q / t.",
        "expected_reasoning": "Current measures the charge flow rate (Q/t), measured in Coulombs per second (Amperes).",
        "distractors": {
            "Total electrical energy stored in a cell": "Confuses current (flow rate of charge) with stored potential energy.",
            "Opposition offered to moving charges": "Confuses current with electrical resistance."
        }
    },
    {
        "concept_id": "electric-current",
        "prompt": "A current of 0.5 A is drawn by a filament of an electric bulb for 10 minutes. What is the total electric charge that flows through the circuit?",
        "difficulty": 2,
        "question_type": "numerical",
        "options": ["300 Coulombs", "5 Coulombs", "50 Coulombs", "1200 Coulombs"],
        "correct_answer": "300 Coulombs",
        "explanation": "Convert time to seconds: t = 10 min * 60 s = 600 s. Using Q = I * t, Q = 0.5 A * 600 s = 300 C.",
        "expected_reasoning": "Must convert time from minutes into standard SI seconds before using Q = I * t.",
        "distractors": {
            "5 Coulombs": "Did not convert minutes to seconds; multiplied 0.5 by 10 instead of 600.",
            "50 Coulombs": "Calculation error in time conversion."
        }
    },
    {
        "concept_id": "electric-current",
        "prompt": "Counterfactual Reasoning: Current enters a glowing electric lamp from the live wire. How does the current exiting the lamp back to the neutral wire compare with the entering current?",
        "difficulty": 3,
        "question_type": "counterfactual",
        "options": ["It is exactly equal to the entering current", "It is less because some current was consumed to produce light", "It is zero because all current is converted into light and heat", "It is greater because electrons accelerate through the filament"],
        "correct_answer": "It is exactly equal to the entering current",
        "explanation": "Electric charge is conserved. Current is the rate of flow of charge; charge is neither created nor destroyed in the bulb. The bulb converts electrical potential energy into light and thermal energy, but electron flow rate remains conserved.",
        "expected_reasoning": "Charge conservation principle: current (electrons) does not get 'used up'; energy is transformed, not charge.",
        "distractors": {
            "It is less because some current was consumed to produce light": "Current Attenuation Misconception: Falsely believing electric current is consumed by appliances."
        }
    },

    # 2. Potential Difference (3 questions)
    {
        "concept_id": "potential-difference",
        "prompt": "What does an electric potential difference of 1 Volt between two points physically mean?",
        "difficulty": 1,
        "question_type": "conceptual",
        "options": ["1 Joule of work is done in moving 1 Coulomb of charge", "1 Ampere of current flows through 1 meter of wire", "1 Watt of power is generated in 1 second", "1 Coulomb of charge is stored at 1 Ohm resistance"],
        "correct_answer": "1 Joule of work is done in moving 1 Coulomb of charge",
        "explanation": "By definition, V = W / Q. 1 Volt equals 1 Joule of work per 1 Coulomb of transferred charge (1 V = 1 J/C).",
        "expected_reasoning": "Voltage represents work done (energy transfer) per unit electric charge.",
        "distractors": {
            "1 Ampere of current flows through 1 meter of wire": "Confuses potential difference with current and conductor length."
        }
    },
    {
        "concept_id": "potential-difference",
        "prompt": "How much work is done in moving a charge of 3 C across two points having a potential difference of 15 V?",
        "difficulty": 2,
        "question_type": "numerical",
        "options": ["45 Joules", "5 Joules", "0.2 Joules", "18 Joules"],
        "correct_answer": "45 Joules",
        "explanation": "From V = W / Q, the work done is W = V * Q = 15 V * 3 C = 45 Joules.",
        "expected_reasoning": "Work equals potential difference multiplied by charge: W = V * Q.",
        "distractors": {
            "5 Joules": "Formula inversion: divided voltage by charge (15 / 3) instead of multiplying W = V * Q.",
            "0.2 Joules": "Divided charge by voltage (3 / 15)."
        }
    },
    {
        "concept_id": "potential-difference",
        "prompt": "Application: Why is a voltmeter always connected in parallel across the two points whose potential difference is to be measured?",
        "difficulty": 3,
        "question_type": "application",
        "options": ["Because parallel components share the same potential difference and a voltmeter has very high resistance to avoid drawing current", "Because voltmeters have zero resistance and would block current if in series", "Because current in parallel is always larger than in series", "Because voltage only exists across parallel components"],
        "correct_answer": "Because parallel components share the same potential difference and a voltmeter has very high resistance to avoid drawing current",
        "explanation": "Potential difference is a property between two distinct points. A voltmeter has an extremely high internal resistance and is connected in parallel so it experiences the exact branch voltage without drawing significant current from the circuit.",
        "expected_reasoning": "Voltmeters measure across two nodes without altering circuit current due to high input impedance.",
        "distractors": {
            "Because voltmeters have zero resistance and would block current if in series": "Confuses voltmeter properties with ammeter properties (ammeters have very low resistance)."
        }
    },

    # 3. Resistance (3 questions)
    {
        "concept_id": "resistance",
        "prompt": "What is the primary physical cause of electrical resistance in a metallic conductor?",
        "difficulty": 1,
        "question_type": "conceptual",
        "options": ["Collisions between drifting electrons and vibrating metal lattice ions", "Friction between the surface of the wire and atmospheric air", "Repulsion between the battery terminals and wire insulation", "Loss of mass from electrons escaping into the room"],
        "correct_answer": "Collisions between drifting electrons and vibrating metal lattice ions",
        "explanation": "As electrons drift through a conductor under an electric field, they frequently collide with the positive metal ions in the crystal lattice, impeding their forward flow. This opposition is resistance.",
        "expected_reasoning": "Microscopic model of conduction: drift electrons collide with lattice ions.",
        "distractors": {
            "Friction between the surface of the wire and atmospheric air": "Confuses mechanical external friction with atomic-level electrical conduction."
        }
    },
    {
        "concept_id": "resistance",
        "prompt": "A conductor allows 2 A of current to pass when connected across a 10 V battery. What is its electrical resistance?",
        "difficulty": 2,
        "question_type": "numerical",
        "options": ["5 Ohms", "20 Ohms", "0.2 Ohms", "12 Ohms"],
        "correct_answer": "5 Ohms",
        "explanation": "R = V / I = 10 V / 2 A = 5 Ω.",
        "expected_reasoning": "Resistance is the ratio of potential difference to current: R = V / I.",
        "distractors": {
            "20 Ohms": "Multiplied voltage times current (10 * 2) instead of dividing R = V / I.",
            "0.2 Ohms": "Divided current by voltage (2 / 10)."
        }
    },
    {
        "concept_id": "resistance",
        "prompt": "Counterfactual Reasoning: If the temperature of a metallic wire conductor increases significantly, what happens to its electrical resistance?",
        "difficulty": 3,
        "question_type": "counterfactual",
        "options": ["It increases because lattice ions vibrate more vigorously, causing more frequent collisions", "It decreases because heating supplies energy that speeds up electrons with less resistance", "It remains constant because resistance only depends on the dimensions of the wire", "It drops to zero because heat converts the wire into a superconductor"],
        "correct_answer": "It increases because lattice ions vibrate more vigorously, causing more frequent collisions",
        "explanation": "Higher temperature increases the thermal kinetic energy of the metal ions in the lattice, causing them to oscillate with larger amplitudes. This increases the probability and frequency of electron-ion collisions, raising resistance.",
        "expected_reasoning": "Temperature dependence: higher thermal lattice vibration increases scattering and resistance in metals.",
        "distractors": {
            "It decreases because heating supplies energy that speeds up electrons with less resistance": "Fails to account for lattice vibration scattering in metals (confuses metal with semiconductor behavior)."
        }
    },

    # 4. Factors Affecting Resistance (3 questions)
    {
        "concept_id": "factors-affecting-resistance",
        "prompt": "According to the resistivity formula R = ρL/A, how does the electrical resistance of a wire vary with its cross-sectional area A?",
        "difficulty": 1,
        "question_type": "conceptual",
        "options": ["Inversely proportional to area: a thicker wire has lower resistance", "Directly proportional to area: a thicker wire has higher resistance", "Independent of area: area only affects wire weight", "Directly proportional to area squared"],
        "correct_answer": "Inversely proportional to area: a thicker wire has lower resistance",
        "explanation": "Resistance R is inversely proportional to cross-sectional area A (R ∝ 1/A). A thicker wire provides more parallel pathways for electrons, thus lowering resistance.",
        "expected_reasoning": "R ∝ 1/A: greater cross-sectional area offers more conduction paths.",
        "distractors": {
            "Directly proportional to area: a thicker wire has higher resistance": "Inverse relationship error: mistakenly thinks bigger wire means bigger resistance."
        }
    },
    {
        "concept_id": "factors-affecting-resistance",
        "prompt": "A cylindrical wire of length L and resistance R is cut into three equal parts. What is the resistance of each individual part?",
        "difficulty": 2,
        "question_type": "numerical",
        "options": ["R / 3", "3 * R", "R / 9", "R"],
        "correct_answer": "R / 3",
        "explanation": "Since R is directly proportional to length L (R ∝ L) while area and material remain unchanged, reducing length to L/3 reduces resistance to R/3.",
        "expected_reasoning": "Direct proportionality between resistance and length (R ∝ L).",
        "distractors": {
            "3 * R": "Inversion error: multiplied by 3 instead of dividing.",
            "R / 9": "Confused linear length cut with volume-conserved wire stretching."
        }
    },
    {
        "concept_id": "factors-affecting-resistance",
        "prompt": "Counterfactual Reasoning: A uniform cylindrical metal wire of resistance R is stretched so that its length is doubled while its total volume remains unchanged. What is its new resistance?",
        "difficulty": 4,
        "question_type": "counterfactual",
        "options": ["4 * R", "2 * R", "R / 2", "R / 4"],
        "correct_answer": "4 * R",
        "explanation": "Since volume V = L * A is constant, doubling length (L' = 2L) causes cross-sectional area to halve (A' = A/2). Therefore: R' = ρ * (2L) / (A/2) = 4 * (ρL/A) = 4R.",
        "expected_reasoning": "Must account for simultaneous length doubling and cross-sectional area halving to conserve volume.",
        "distractors": {
            "2 * R": "Unidimensional error: tracked length doubling but forgot that cross-sectional area halves when stretched."
        }
    },

    # 5. Ohm's Law (3 questions)
    {
        "concept_id": "ohms-law",
        "prompt": "Which condition is strictly required for a conductor to obey Ohm's Law (V = IR)?",
        "difficulty": 1,
        "question_type": "conceptual",
        "options": ["Temperature and other physical conditions must remain constant", "The current must alternate in direction every second", "The circuit must contain at least three different resistors", "The conductor must be made of insulating rubber"],
        "correct_answer": "Temperature and other physical conditions must remain constant",
        "explanation": "Ohm's Law states that current is directly proportional to voltage across a conductor provided its temperature, mechanical strain, and physical dimensions remain constant.",
        "expected_reasoning": "Ohm's law validity requires constant physical conditions, especially temperature.",
        "distractors": {
            "The current must alternate in direction every second": "Confused DC/AC waveforms with Ohm's law linearity."
        }
    },
    {
        "concept_id": "ohms-law",
        "prompt": "An electric iron draws 3.5 A of current from a 220 V supply line. What is the resistance of the electric iron heating element?",
        "difficulty": 2,
        "question_type": "numerical",
        "options": ["62.86 Ohms", "770 Ohms", "0.016 Ohms", "216.5 Ohms"],
        "correct_answer": "62.86 Ohms",
        "explanation": "From V = IR, R = V / I = 220 V / 3.5 A ≈ 62.86 Ω.",
        "expected_reasoning": "Using Ohm's law formula R = V / I.",
        "distractors": {
            "770 Ohms": "Formula inversion: multiplied 220 * 3.5 instead of dividing.",
            "0.016 Ohms": "Inverted division: divided 3.5 / 220."
        }
    },
    {
        "concept_id": "ohms-law",
        "prompt": "Counterfactual Scenario: In an ohmic circuit, if the applied voltage is increased by 50% while the resistance is simultaneously reduced to half its initial value, the new current will be:",
        "difficulty": 3,
        "question_type": "counterfactual",
        "options": ["3 times the original current", "1.5 times the original current", "0.75 times the original current", "The same as the original current"],
        "correct_answer": "3 times the original current",
        "explanation": "Original I = V / R. New voltage V' = 1.5 V, new resistance R' = 0.5 R. Therefore I' = (1.5 V) / (0.5 R) = 3 * (V / R) = 3 I.",
        "expected_reasoning": "Simultaneous variable substitution into I = V / R: 1.5 / 0.5 = 3.",
        "distractors": {
            "1.5 times the original current": "Only accounted for voltage increase and ignored the resistance halving."
        }
    },

    # 6. Series Circuits (3 questions)
    {
        "concept_id": "series-circuits",
        "prompt": "In a series circuit containing three resistors of 5 Ω, 10 Ω, and 15 Ω, which statement is physically correct?",
        "difficulty": 1,
        "question_type": "conceptual",
        "options": ["The same electric current flows through each resistor, and equivalent resistance is 30 Ω", "The voltage across each resistor is identical regardless of resistance", "The total equivalent resistance is less than 5 Ω", "If one resistor is removed, the remaining two resistors glow twice as bright"],
        "correct_answer": "The same electric current flows through each resistor, and equivalent resistance is 30 Ω",
        "explanation": "In a series circuit, there is only one continuous path for charge flow, so current is identical in every element. Equivalent resistance is the direct arithmetic sum: Req = 5 + 10 + 15 = 30 Ω.",
        "expected_reasoning": "Series rules: common current throughout, additive equivalent resistance.",
        "distractors": {
            "The voltage across each resistor is identical regardless of resistance": "Confuses series circuit behavior with parallel circuit behavior.",
            "The total equivalent resistance is less than 5 Ω": "Applies parallel equivalent resistance rule to series."
        }
    },
    {
        "concept_id": "series-circuits",
        "prompt": "Two resistors of 4 Ω and 6 Ω are connected in series across a 20 V battery. What is the potential difference across the 6 Ω resistor?",
        "difficulty": 2,
        "question_type": "numerical",
        "options": ["12 Volts", "8 Volts", "20 Volts", "2 Volts"],
        "correct_answer": "12 Volts",
        "explanation": "Total resistance Req = 4 + 6 = 10 Ω. Circuit current I = V / Req = 20 V / 10 Ω = 2 A. Voltage across 6 Ω resistor is V2 = I * R2 = 2 A * 6 Ω = 12 V.",
        "expected_reasoning": "Calculate total series resistance, find circuit current, then apply Ohm's law to target resistor.",
        "distractors": {
            "8 Volts": "Calculated voltage across the 4 Ω resistor instead of the 6 Ω resistor.",
            "20 Volts": "Assumed the entire battery voltage appears across a single series resistor."
        }
    },
    {
        "concept_id": "series-circuits",
        "prompt": "Application: Why are decorative festive fairy lights often considered impractical when all bulbs are wired strictly in series?",
        "difficulty": 3,
        "question_type": "application",
        "options": ["If one bulb filament burns out, the circuit opens and every single bulb goes dark", "The bulbs would draw too much current and immediately blow the house fuse", "Every bulb would experience 240 V independently and explode", "The overall resistance would become zero"],
        "correct_answer": "If one bulb filament burns out, the circuit opens and every single bulb goes dark",
        "explanation": "Because a series circuit is a single closed loop, any break or burned-out filament creates an open circuit, stopping current completely across all connected components.",
        "expected_reasoning": "Single loop dependency: one broken component breaks continuity for all.",
        "distractors": {
            "The bulbs would draw too much current and immediately blow the house fuse": "Series resistance actually limits total current, not increases it."
        }
    },

    # 7. Parallel Circuits (3 questions)
    {
        "concept_id": "parallel-circuits",
        "prompt": "What is the primary characteristic of electrical potential difference in a parallel circuit with multiple branches?",
        "difficulty": 1,
        "question_type": "conceptual",
        "options": ["The potential difference across every parallel branch is identical", "The potential difference divides inversely according to branch resistance", "The voltage drops to zero after passing through the first branch", "Total voltage equals the sum of branch voltages"],
        "correct_answer": "The potential difference across every parallel branch is identical",
        "explanation": "All parallel branches connect between the same pair of common electrical nodes, ensuring that the full supply potential difference is applied directly across each branch.",
        "expected_reasoning": "Parallel branches share common junctions, guaranteeing identical voltage across each branch.",
        "distractors": {
            "Total voltage equals the sum of branch voltages": "Confuses parallel voltage rule with series voltage divider rule."
        }
    },
    {
        "concept_id": "parallel-circuits",
        "prompt": "Two resistors of 12 Ω and 4 Ω are connected in parallel. What is their combined equivalent resistance?",
        "difficulty": 2,
        "question_type": "numerical",
        "options": ["3 Ohms", "16 Ohms", "8 Ohms", "0.33 Ohms"],
        "correct_answer": "3 Ohms",
        "explanation": "1/Req = 1/12 + 1/4 = 1/12 + 3/12 = 4/12 = 1/3. Therefore Req = 3 Ω.",
        "expected_reasoning": "Reciprocal addition formula for parallel resistors: 1/Req = 1/R1 + 1/R2.",
        "distractors": {
            "16 Ohms": "Direct addition error: added 12 + 4 directly using the series formula.",
            "8 Ohms": "Averaged the two resistances instead of reciprocal calculation."
        }
    },
    {
        "concept_id": "parallel-circuits",
        "prompt": "Counterfactual Reasoning: A 12 V battery powers two parallel resistors. If a third parallel branch with a resistor is added to the circuit, what happens to the total current drawn from the battery?",
        "difficulty": 3,
        "question_type": "counterfactual",
        "options": ["Total current increases because equivalent resistance decreases", "Total current decreases because more resistors always restrict total flow", "Total current remains exactly the same", "The battery voltage doubles"],
        "correct_answer": "Total current increases because equivalent resistance decreases",
        "explanation": "Adding a parallel branch creates an additional conductive pathway for charges to flow. Equivalent resistance decreases, so the battery must supply the existing branch currents plus the new branch current, increasing total current.",
        "expected_reasoning": "Adding parallel branches reduces equivalent resistance and increases total current drawn from source.",
        "distractors": {
            "Total current decreases because more resistors always restrict total flow": "Common misconception: believing that adding any resistor anywhere in a circuit always restricts total flow."
        }
    },

    # 8. Electrical Power (3 questions)
    {
        "concept_id": "electrical-power",
        "prompt": "Which formula does NOT represent electrical power in an ohmic circuit?",
        "difficulty": 1,
        "question_type": "conceptual",
        "options": ["P = I * R^2", "P = V * I", "P = I^2 * R", "P = V^2 / R"],
        "correct_answer": "P = I * R^2",
        "explanation": "Power is defined as P = VI. Substituting V = IR gives P = I^2R. Substituting I = V/R gives P = V^2/R. The expression I*R^2 is dimensionally incorrect (has units of V*R, not Watts).",
        "expected_reasoning": "P = VI = I^2R = V^2/R. I*R^2 is physically invalid.",
        "distractors": {
            "P = I^2 * R": "This is a valid power formula.",
            "P = V^2 / R": "This is a valid power formula."
        }
    },
    {
        "concept_id": "electrical-power",
        "prompt": "An electric refrigerator rated 400 W operates 8 hours/day. What is the cost of energy to operate it for 30 days at ₹3.00 per kWh?",
        "difficulty": 2,
        "question_type": "numerical",
        "options": ["₹ 288.00", "₹ 96.00", "₹ 28.80", "₹ 960.00"],
        "correct_answer": "₹ 288.00",
        "explanation": "Total energy = 400 W * 8 h/day * 30 days = 96,000 Wh = 96 kWh. Cost = 96 kWh * ₹3.00/kWh = ₹288.00.",
        "expected_reasoning": "Energy = Power * time. Convert Watt-hours to commercial units (Kilowatt-hours) before multiplying by unit rate.",
        "distractors": {
            "₹ 96.00": "Forgot to multiply by the cost rate per kWh.",
            "₹ 28.80": "Decimal point conversion error."
        }
    },
    {
        "concept_id": "electrical-power",
        "prompt": "Counterfactual Reasoning: An electric heater element is connected to a fixed supply voltage V. If the heating coil is cut in half so its resistance halves, the power output of the heater will:",
        "difficulty": 3,
        "question_type": "counterfactual",
        "options": ["Double (increase by 2x)", "Halve (decrease by 2x)", "Quadruple (increase by 4x)", "Remain unchanged"],
        "correct_answer": "Double (increase by 2x)",
        "explanation": "Since supply voltage V is constant, we use P = V^2 / R. When resistance R is halved (R' = R/2), P' = V^2 / (R/2) = 2 * (V^2 / R) = 2P.",
        "expected_reasoning": "At constant voltage, power is inversely proportional to resistance (P = V^2 / R).",
        "distractors": {
            "Halve (decrease by 2x)": "Misapplied P = I^2R assuming current remained constant rather than voltage."
        }
    },

    # 9. Heating Effect of Electric Current (3 questions)
    {
        "concept_id": "heating-effect",
        "prompt": "According to Joule's Law of Heating, the heat H produced in a resistor R over time t is proportional to:",
        "difficulty": 1,
        "question_type": "conceptual",
        "options": ["The square of the current (I^2)", "The square root of the current (√I)", "The inverse of the current (1/I)", "The square of time (t^2)"],
        "correct_answer": "The square of the current (I^2)",
        "explanation": "Joule's Law of heating states that H = I^2 * R * t: heat generated is directly proportional to the square of current (I^2), resistance (R), and duration of flow (t).",
        "expected_reasoning": "Joule's Law: H = I^2 * R * t.",
        "distractors": {
            "The inverse of the current (1/I)": "Incorrect relationship.",
            "The square of time (t^2)": "Heat depends linearly on time, not quadratically."
        }
    },
    {
        "concept_id": "heating-effect",
        "prompt": "100 Joules of heat are produced each second in a 4 Ω resistor. What is the potential difference across the resistor?",
        "difficulty": 2,
        "question_type": "numerical",
        "options": ["20 Volts", "25 Volts", "400 Volts", "5 Volts"],
        "correct_answer": "20 Volts",
        "explanation": "Heat per second is power: P = H/t = 100 J/s = 100 W. Using P = V^2 / R => V^2 = P * R = 100 * 4 = 400. Therefore V = √400 = 20 V.",
        "expected_reasoning": "Power P = 100 W. Solve for voltage using P = V^2 / R.",
        "distractors": {
            "25 Volts": "Divided 100 by 4 instead of multiplying V^2 = P * R.",
            "400 Volts": "Forgot to take the square root of V^2 = 400."
        }
    },
    {
        "concept_id": "heating-effect",
        "prompt": "Application & Safety: Why is an electric fuse wire made of a material having high resistivity and a relatively low melting point?",
        "difficulty": 3,
        "question_type": "application",
        "options": ["High resistivity produces rapid Joule heating (H = I^2Rt) during overcurrent, and the low melting point quickly breaks the circuit safely", "Low melting point prevents the wire from ever heating up during use", "To conduct infinite current without heating the surrounding plug", "Because high resistivity allows unlimited voltage to pass to home appliances"],
        "correct_answer": "High resistivity produces rapid Joule heating (H = I^2Rt) during overcurrent, and the low melting point quickly breaks the circuit safely",
        "explanation": "A fuse is a critical safety device. When current exceeds safe thresholds, high resistance produces rapid heating via H = I^2Rt. The low melting point causes the wire to melt promptly, breaking the circuit and preventing electrical fires or equipment damage.",
        "expected_reasoning": "Fuse operation depends on Joule heating melting a sacrificial link with a calibrated melting point.",
        "distractors": {
            "Low melting point prevents the wire from ever heating up during use": "Misunderstands how melting point works (melting point determines when the wire breaks, not heat production)."
        }
    }
]

def seed_database(db: Session):
    """
    Populates database with initial curriculum concepts, prerequisite edges,
    and the 27+ comprehensive Class 10 Electricity questions.
    Ensures idempotency (no duplicate entries on server restart).
    """
    # 1. Seed Concepts
    for c_data in CONCEPTS_DATA:
        existing = db.query(Concept).filter(Concept.id == c_data["id"]).first()
        if not existing:
            db.add(Concept(**c_data))
        else:
            existing.title = c_data["title"]
            existing.description = c_data["description"]
            existing.category = c_data["category"]
            existing.order_index = c_data["order_index"]
    db.commit()

    # 2. Seed Concept Prerequisites
    for parent_id, child_id in PREREQUISITES_DATA:
        existing = db.query(ConceptPrerequisite).filter(
            ConceptPrerequisite.parent_id == parent_id,
            ConceptPrerequisite.child_id == child_id
        ).first()
        if not existing:
            db.add(ConceptPrerequisite(parent_id=parent_id, child_id=child_id))
    db.commit()

    # 3. Seed Questions
    for q_data in QUESTIONS_DATA:
        existing = db.query(Question).filter(Question.prompt == q_data["prompt"]).first()
        if not existing:
            new_q = Question(
                concept_id=q_data["concept_id"],
                prompt=q_data["prompt"],
                difficulty=q_data["difficulty"],
                question_type=q_data.get("question_type", "conceptual"),
                options_json=json.dumps(q_data["options"]),
                correct_answer=q_data["correct_answer"],
                explanation=q_data["explanation"],
                expected_reasoning=q_data["expected_reasoning"],
                misconception_distractor_map=json.dumps(q_data.get("distractors", {}))
            )
            db.add(new_q)
        else:
            existing.concept_id = q_data["concept_id"]
            existing.difficulty = q_data["difficulty"]
            existing.question_type = q_data.get("question_type", "conceptual")
            existing.options_json = json.dumps(q_data["options"])
            existing.correct_answer = q_data["correct_answer"]
            existing.explanation = q_data["explanation"]
            existing.expected_reasoning = q_data["expected_reasoning"]
            existing.misconception_distractor_map = json.dumps(q_data.get("distractors", {}))
    db.commit()
