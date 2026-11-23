// ekcal: ferramenta mínima de calendário via EventKit (sincroniza com o iCloud).
//
// Uso:
//   ekcal sources                                  lista contas e calendários
//   ekcal ensure <calendário>                      cria o calendário no iCloud, se não existir
//   ekcal delete-series <calendário> <título>      apaga a série inteira (todas as ocorrências)
//   ekcal delete-range <calendário> <de> <até> [prefixo-nota]
//                                                   apaga eventos no intervalo (AAAA-MM-DD); se houver
//                                                   prefixo, só os eventos cuja nota começa com ele
//   ekcal add <calendário> <arquivo.json>          cria eventos: [{"titulo","inicio":"AAAA-MM-DD HH:MM","min","notas","alerta"}]
//   ekcal remove-calendar <calendário> <conta>     apaga um calendário inteiro de uma conta (ex.: "On My Mac")
import EventKit
import Foundation

let store = EKEventStore()
let sem = DispatchSemaphore(value: 0)
var ok = false
store.requestFullAccessToEvents { granted, _ in ok = granted; sem.signal() }
sem.wait()
guard ok else { print("ERRO: sem acesso ao calendário (Ajustes → Privacidade → Calendários)"); exit(2) }

let args = Array(CommandLine.arguments.dropFirst())
let fmtDia = DateFormatter(); fmtDia.dateFormat = "yyyy-MM-dd"
let fmtHora = DateFormatter(); fmtHora.dateFormat = "yyyy-MM-dd HH:mm"

func icloud() -> EKSource? {
    store.sources.first { $0.sourceType == .calDAV && $0.title.lowercased().contains("icloud") }
}
func cal(_ nome: String, conta: String? = nil) -> EKCalendar? {
    store.calendars(for: .event).first { $0.title == nome && (conta == nil || $0.source.title == conta) }
}
func calICloud(_ nome: String) -> EKCalendar? {
    store.calendars(for: .event).first { $0.title == nome && $0.source.sourceType == .calDAV }
}

switch args.first ?? "" {
case "sources":
    for c in store.calendars(for: .event) {
        print("\(c.source.title) [\(c.source.sourceType.rawValue)] · \(c.title) · editável: \(c.allowsContentModifications)")
    }
case "ensure":
    let nome = args[1]
    if let c = calICloud(nome) { print("já existe no iCloud: \(c.title)"); break }
    guard let src = icloud() else { print("ERRO: conta iCloud não encontrada"); exit(1) }
    let c = EKCalendar(for: .event, eventStore: store)
    c.title = nome
    c.source = src
    c.cgColor = CGColor(red: 0.11, green: 0.37, blue: 0.82, alpha: 1)
    try store.saveCalendar(c, commit: true)
    print("criado no iCloud: \(nome)")
case "delete-series":
    guard let c = cal(args[1]) else { print("ERRO: calendário não encontrado"); exit(1) }
    let titulo = args[2]
    let ini = Date(timeIntervalSinceNow: -60 * 60 * 24 * 365 * 6)
    var apagados = 0
    // a busca do EventKit aceita no máximo ~4 anos por vez
    var a = ini
    while a < Date(timeIntervalSinceNow: 60 * 60 * 24 * 365 * 2) {
        let b = a.addingTimeInterval(60 * 60 * 24 * 365 * 3)
        let evs = store.events(matching: store.predicateForEvents(withStart: a, end: b, calendars: [c]))
            .filter { $0.title == titulo }
            .sorted { $0.startDate < $1.startDate }
        if let primeiro = evs.first {
            try store.remove(primeiro, span: .futureEvents, commit: true)
            apagados += 1
        }
        a = b
    }
    print("\(titulo): séries/ocorrências removidas a partir da primeira encontrada (\(apagados) chamada(s))")
case "delete-range":
    guard let c = calICloud(args[1]) ?? cal(args[1]) else { print("ERRO: calendário não encontrado"); exit(1) }
    let de = fmtDia.date(from: args[2])!, ate = fmtDia.date(from: args[3])!.addingTimeInterval(86400)
    let prefixo = args.count > 4 ? args[4] : nil
    let evs = store.events(matching: store.predicateForEvents(withStart: de, end: ate, calendars: [c]))
        .filter { prefixo == nil || ($0.notes ?? "").hasPrefix(prefixo!) }
    for e in evs { try store.remove(e, span: .thisEvent, commit: false) }
    try store.commit()
    print("apagados: \(evs.count)")
case "add":
    guard let c = calICloud(args[1]) else { print("ERRO: calendário iCloud não encontrado"); exit(1) }
    let dados = try Data(contentsOf: URL(fileURLWithPath: args[2]))
    let lista = try JSONSerialization.jsonObject(with: dados) as! [[String: Any]]
    for item in lista {
        let e = EKEvent(eventStore: store)
        e.calendar = c
        e.title = item["titulo"] as? String
        e.startDate = fmtHora.date(from: item["inicio"] as! String)!
        e.endDate = e.startDate.addingTimeInterval(Double(item["min"] as! Int) * 60)
        e.notes = item["notas"] as? String
        if let u = item["url"] as? String { e.url = URL(string: u) }
        if let al = item["alerta"] as? Int { e.addAlarm(EKAlarm(relativeOffset: Double(-al * 60))) }
        try store.save(e, span: .thisEvent, commit: false)
    }
    try store.commit()
    print("criados: \(lista.count)")
case "remove-calendar":
    guard let c = cal(args[1], conta: args[2]) else { print("não existe: \(args[1]) em \(args[2])"); break }
    try store.removeCalendar(c, commit: true)
    print("calendário removido: \(args[1]) (\(args[2]))")
default:
    print("comandos: sources | ensure | delete-series | delete-range | add | remove-calendar")
}
