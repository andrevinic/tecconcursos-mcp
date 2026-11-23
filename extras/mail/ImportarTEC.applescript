-- Regra do Mail (macOS): importa sozinho a planilha que o TecConcursos manda por e-mail.
--
-- O e-mail "Sua exportação de estatísticas está pronta" não traz anexo, só um link (vale 7 dias).
-- Este script entrega o código-fonte do e-mail ao `tecconcursos-mcp baixar-email`, que baixa a
-- planilha, descarta exports repetidos (mesmas células) e importa para a pasta de exports.
--
-- Instalação:
--   osacompile -o ~/Library/Application\ Scripts/com.apple.mail/ImportarTEC.scpt ImportarTEC.applescript
--   Mail → Ajustes → Regras → Adicionar: "De" contém "tecconcursos" → Executar AppleScript → ImportarTEC
-- Teste: selecione o e-mail do TEC e use Mensagem → Aplicar Regras (⌥⌘L).
using terms from application "Mail"
	on perform mail action with messages theMessages for rule theRule
		set cli to (POSIX path of (path to home folder)) & ".local/bin/tecconcursos-mcp"
		repeat with msg in theMessages
			tell application "Mail" to set fonte to source of msg
			set tmp to do shell script "mktemp -t tecmail"
			set f to open for access (POSIX file tmp) with write permission
			write fonte to f as «class utf8»
			close access f
			try
				set saida to do shell script quoted form of cli & " baixar-email " & quoted form of tmp
			on error e
				set saida to "erro: " & e
			end try
			do shell script "rm -f " & quoted form of tmp
			if saida does not contain "sem link" then display notification saida with title "TecConcursos"
		end repeat
	end perform mail action with messages
end using terms from
