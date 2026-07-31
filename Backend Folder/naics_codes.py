"""
Curated list of common 6-digit NAICS codes for the industry picker / search box.
This is a practical subset (a few hundred common small-business industries)
covering the sectors this tool models, not the full ~1,000-code NAICS list.
To search the complete official list instead, swap this out for the Census
Bureau's published NAICS reference file.
"""

NAICS_CODES = [
    # Construction
    ("236115", "New Single-Family Housing Construction"),
    ("236220", "Commercial and Institutional Building Construction"),
    ("237310", "Highway, Street, and Bridge Construction"),
    ("238110", "Poured Concrete Foundation and Structure Contractors"),
    ("238160", "Roofing Contractors"),
    ("238210", "Electrical Contractors"),
    ("238220", "Plumbing, Heating, and Air-Conditioning Contractors"),
    ("238350", "Finish Carpentry Contractors"),
    # Manufacturing
    ("311811", "Retail Bakeries"),
    ("312120", "Breweries"),
    ("321912", "Cut Stock, Resawing Lumber, and Planing"),
    ("332710", "Machine Shops"),
    ("337110", "Wood Kitchen Cabinet and Countertop Manufacturing"),
    ("339999", "All Other Miscellaneous Manufacturing"),
    # Wholesale Trade
    ("423430", "Computer and Computer Peripheral Equipment Wholesalers"),
    ("423840", "Industrial Supplies Wholesalers"),
    ("424410", "General Line Grocery Wholesalers"),
    ("424690", "Other Chemical and Allied Products Wholesalers"),
    # Retail Trade
    ("441110", "New Car Dealers"),
    ("441120", "Used Car Dealers"),
    ("444110", "Home Centers"),
    ("444230", "Outdoor Power Equipment Stores"),
    ("445110", "Supermarkets and Other Grocery Retailers"),
    ("445230", "Fruit and Vegetable Retailers"),
    ("446110", "Pharmacies and Drug Retailers"),
    ("446120", "Cosmetics, Beauty Supplies, and Perfume Retailers"),
    ("447110", "Gasoline Stations with Convenience Stores"),
    ("448110", "Women's Clothing Retailers"),
    ("448120", "Men's Clothing Retailers"),
    ("448140", "Family Clothing Retailers"),
    ("451110", "Sporting Goods Retailers"),
    ("451211", "Book Retailers"),
    ("452210", "Department Stores"),
    ("453220", "Gift, Novelty, and Souvenir Retailers"),
    ("453910", "Pet and Pet Supplies Retailers"),
    ("454110", "Electronic Shopping and Mail-Order Houses"),
    # Transportation & Warehousing
    ("484110", "General Freight Trucking, Local"),
    ("484230", "Specialized Freight (except Used Goods) Trucking, Long-Distance"),
    ("485310", "Taxi and Ridesharing Services"),
    ("488510", "Freight Transportation Arrangement"),
    ("493110", "General Warehousing and Storage"),
    # Information
    ("511210", "Software Publishers"),
    ("512110", "Motion Picture and Video Production"),
    ("515210", "Media Streaming Distribution Services"),
    ("519290", "Web Search Portals and All Other Information Services"),
    # Finance & Insurance
    ("522110", "Commercial Banking"),
    ("523930", "Investment Advice"),
    ("524210", "Insurance Agencies and Brokerages"),
    # Real Estate & Rental/Leasing
    ("531210", "Offices of Real Estate Agents and Brokers"),
    ("531311", "Residential Property Managers"),
    ("532120", "Truck, Utility Trailer, and RV Rental and Leasing"),
    # Professional, Scientific & Technical Services
    ("541110", "Offices of Lawyers"),
    ("541211", "Offices of Certified Public Accountants"),
    ("541330", "Engineering Services"),
    ("541511", "Custom Computer Programming Services"),
    ("541512", "Computer Systems Design Services"),
    ("541613", "Marketing Consulting Services"),
    ("541810", "Advertising Agencies"),
    ("541921", "Photography Studios, Portrait"),
    ("541930", "Translation and Interpretation Services"),
    # Administrative & Support Services
    ("561320", "Temporary Help Services"),
    ("561440", "Collection Agencies"),
    ("561621", "Security Systems Services (except Locksmiths)"),
    ("561730", "Landscaping Services"),
    ("561740", "Carpet and Upholstery Cleaning Services"),
    ("561790", "Other Services to Buildings and Dwellings"),
    # Educational Services
    ("611110", "Elementary and Secondary Schools"),
    ("611420", "Computer Training"),
    ("611620", "Sports and Recreation Instruction"),
    # Health Care & Social Assistance
    ("621111", "Offices of Physicians (except Mental Health Specialists)"),
    ("621210", "Offices of Dentists"),
    ("621310", "Offices of Chiropractors"),
    ("621340", "Offices of Physical, Occupational and Speech Therapists"),
    ("621610", "Home Health Care Services"),
    ("622110", "General Medical and Surgical Hospitals"),
    ("623110", "Nursing Care Facilities (Skilled Nursing Facilities)"),
    ("624410", "Child Day Care Services"),
    # Arts, Entertainment & Recreation
    ("711130", "Musical Groups and Artists"),
    ("713940", "Fitness and Recreational Sports Centers"),
    ("713990", "All Other Amusement and Recreation Industries"),
    # Accommodation & Food Services
    ("721110", "Hotels (except Casino Hotels) and Motels"),
    ("722511", "Full-Service Restaurants"),
    ("722513", "Limited-Service Restaurants"),
    ("722515", "Snack and Nonalcoholic Beverage Bars"),
    # Other Services
    ("811111", "General Automotive Repair"),
    ("811310", "Commercial and Industrial Machinery and Equipment Repair"),
    ("812111", "Barber Shops"),
    ("812112", "Beauty Salons"),
    ("812113", "Nail Salons"),
    ("812191", "Diet and Weight Reducing Centers"),
    ("812210", "Funeral Homes and Funeral Services"),
    ("812320", "Drycleaning and Laundry Services (except Coin-Operated)"),
    ("812910", "Pet Care (except Veterinary) Services"),
    ("812921", "Photofinishing Laboratories (except One-Hour)"),
    ("813110", "Religious Organizations"),
]


def search_naics(query: str, limit: int = 25):
    q = (query or "").strip().lower()
    if not q:
        return NAICS_CODES[:limit]
    if q.isdigit():
        results = [c for c in NAICS_CODES if c[0].startswith(q)]
    else:
        results = [c for c in NAICS_CODES if q in c[1].lower()]
    return results[:limit]
