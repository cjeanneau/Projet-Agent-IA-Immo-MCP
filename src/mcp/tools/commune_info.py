def get_commune_info(con, code_insee):
    """
    Retourne un dictionnaire des informations d'une commune à partir de son code INSEE.
    Inclut le nom de la commune et les valeurs de toutes les colonnes.

    Args:
        con: Connexion DuckDB active.
        code_insee (str): Code INSEE de la commune (ex: "01009").

    Returns:
        dict: Dictionnaire des informations de la commune, incluant le nom et les valeurs par colonne.
              Retourne un dictionnaire avec une clé "error" si aucune ligne n'est trouvée.
    """

    # Exécute la requête et récupère le résultat sous forme de DataFrame
    query = f"SELECT * FROM count_equipements WHERE code_insee = '{code_insee}';"
    result = con.execute(query).df()

    # Renomme les colonnes pour correspondre aux noms attendus
    result.columns = [
        'code_insee', 
        'nom_commune', 
        'nombre_equipements_services_publics', 
        'nombre_equipements_sante_social', 
        'nombre_equipements_sport_loisir_culture', 
        'ombre_equipements_enseignement', 
        'nombre_equipements_transport', 
        'nombre_equipements_commerce', 
        'nombre_equipements_tourisme'
    ]

    # Vérifie si le résultat est vide
    if result.shape[0] == 0:
        return {"error" : f"Aucune information associée au code insee {code_insee} n'a été trouvé."}

    # Construire le dictionnaire
    commune_info = result.loc[0].to_dict()
    return commune_info