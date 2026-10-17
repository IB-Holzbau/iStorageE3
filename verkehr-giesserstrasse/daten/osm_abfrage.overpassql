/* Kreuzung Gießerstraße / Naumburger Straße, Leipzig. Alles im Umkreis 150 m. */
[out:json][timeout:120];
area["name"="Leipzig"]["admin_level"="6"]->.lpz;
way["highway"]["name"="Gießerstraße"](area.lpz)->.g;
way["highway"]["name"="Naumburger Straße"](area.lpz)->.n;
node(w.g)->.gn;
node(w.n)->.nn;
node.gn.nn->.k;          /* gemeinsamer Knoten = Kreuzung */
.k out;                  /* Kreuzungsknoten zuerst ausgeben */
(
  way(around.k:150)["highway"];
  way(around.k:150)["railway"];
  way(around.k:150)["parking"];
  way(around.k:150)["amenity"="parking"];
  node(around.k:150)["highway"];
  node(around.k:150)["traffic_sign"];
  node(around.k:150)["crossing"];
  node(around.k:150)["railway"];
  node(around.k:150)["public_transport"];
  relation(around.k:150)["type"="restriction"];
  relation(around.k:150)["route"~"bus|tram"];
)->.alle;
(.alle; >;);
out meta;
