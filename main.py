import os
import discord
from discord import app_commands
import asyncio
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
from threading import Thread

# --- Truco para Render: Servidor Web en segundo plano ---
def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    handler = SimpleHTTPRequestHandler
    TCPServer.allow_reuse_address = True
    with TCPServer(("0.0.0.0", port), handler) as httpd:
        print(f"Health check running on port {port}")
        httpd.serve_forever()

Thread(target=run_health_check, daemon=True).start()

# --- Configuración del Bot de Discord ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# --- IDs de Configuración Generales ---
WELCOME_CH_ID = 1528749785895538849
LEAVE_CH_ID = 1528750006260072621
INVITE_CH_ID = 1528750567738839150

@client.event
async def on_ready():
    print(f"Bot conectado como {client.user.name}")
    await client.change_presence(activity=discord.Game(name="vshop.com"))
    try:
        await tree.sync()
        print("Comandos de barra sincronizados correctamente.")
    except Exception as e:
        print(f"Error al sincronizar comandos: {e}")

# --- COMANDO /VERIFY DINÁMICO ---
@tree.command(name="verify", description="Crea el panel de verificación asignando un rol específico")
@app_commands.describe(rol="Selecciona o escribe el ID del rol que otorgará la verificación")
@app_commands.checks.has_permissions(administrator=True)
async def verify(interaction: discord.Interaction, rol: discord.Role):
    embed = discord.Embed(
        title="🔒 VERIFICACIÓN REQUERIDA — VSHOP",
        description=(
            "Bienvenido a **VSHOP**. Para acceder al resto de los canales, "
            "tiendas y soporte, debes verificar tu cuenta.\n\n"
            "**Instrucciones:**\n"
            "Reacciona a este mensaje con el emoji personalizado `:vshop:` "
            "para obtener tu rol de acceso automáticamente."
        ),
        color=discord.Color.blue()
    )
    
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    
    # Guardamos la ID del rol en el footer
    embed.set_footer(text=f"Seguridad de VSHOP | RoleID:{rol.id}")
    
    await interaction.response.send_message(f"Panel de verificación creado para el rol {rol.mention}.", ephemeral=True)
    message = await interaction.channel.send(embed=embed)
    
    emoji = discord.utils.get(interaction.guild.emojis, name="vshop")
    if emoji:
        await message.add_reaction(emoji)

# --- ROL POR REACCIÓN DINÁMICO ---
@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == client.user.id:
        return
        
    if payload.emoji.name == "vshop":
        guild = client.get_guild(payload.guild_id)
        if not guild: 
            return
            
        channel = guild.get_channel(payload.channel_id)
        if not channel: 
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except Exception:
            return

        if message.embeds:
            embed = message.embeds[0]
            if embed.footer and embed.footer.text and "RoleID:" in embed.footer.text:
                try:
                    role_id = int(embed.footer.text.split("RoleID:")[1])
                    role = guild.get_role(role_id)
                    member = guild.get_member(payload.user_id)
                    
                    if role and member:
                        await member.add_roles(role)
                except Exception as e:
                    print(f"No se pudo otorgar el rol: {e}")

# --- BIENVENIDAS Y DESPEDIDAS ---
@client.event
async def on_member_join(member: discord.Member):
    welcome_channel = client.get_channel(WELCOME_CH_ID)
    if welcome_channel:
        embed = discord.Embed(
            title="👋 ¡Un nuevo miembro ha llegado!",
            description=f"¡Bienvenido/a {member.mention} a **{member.guild.name}**!\nNo olvides verificar tu cuenta.",
            color=discord.Color.green()
        )
        embed.add_field(name="Miembro número", value=f"#{len(member.guild.members)}", inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        await welcome_channel.send(embed=embed)

    invite_channel = client.get_channel(INVITE_CH_ID)
    if invite_channel:
        embed_inv = discord.Embed(
            title="📥 Registro de Entrada",
            description=f"El usuario {member.name} (`{member.id}`) entró al servidor.",
            color=discord.Color.light_gray()
        )
        await invite_channel.send(embed=embed_inv)

@client.event
async def on_member_remove(member: discord.Member):
    leave_channel = client.get_channel(LEAVE_CH_ID)
    if leave_channel:
        embed = discord.Embed(
            title="💔 ¡Alguien nos ha dejado!",
            description=f"Lamentamos ver partir a **{member.name}**.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await leave_channel.send(embed=embed)

# --- COMANDO /AD ---
@tree.command(name="ad", description="Publica un anuncio profesional")
@app_commands.describe(titulo="Título", descripcion="Contenido")
@app_commands.checks.has_permissions(administrator=True)
async def ad(interaction: discord.Interaction, titulo: str, descripcion: str):
    embed = discord.Embed(title=f"📢 {titulo.upper()}", description=descripcion, color=discord.Color.gold())
    embed.set_footer(text=f"Publicado por {interaction.user.name}")
    await interaction.response.send_message("Anuncio enviado.", ephemeral=True)
    await interaction.channel.send(content="@everyone", embed=embed)

# --- SISTEMA DE TICKETS DINÁMICO ---
class TicketButton(discord.ui.View):
    def __init__(self, ticket_type: str):
        super().__init__(timeout=None)
        self.ticket_type = ticket_type

    @discord.ui.button(label="📩 Abrir Ticket", style=discord.ButtonStyle.primary, custom_id="open_ticket_btn")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        category_name = f"🎟️ TICKETS {self.ticket_type.upper()}"
        
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)
            
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            client.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        ticket_channel = await guild.create_text_channel(
            name=f"{self.ticket_type.lower()}-{member.name}", 
            category=category, 
            overwrites=overwrites
        )
        
        embed = discord.Embed(
            title=f"🎟️ Ticket de {self.ticket_type.capitalize()}",
            description=f"Hola {member.mention}, detalla tu consulta o postulación aquí. Un encargado te atenderá pronto.",
            color=discord.Color.green()
        )
        
        close_view = discord.ui.View(timeout=None)
        close_button = discord.ui.Button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.danger)
        
        async def close_callback(inter: discord.Interaction):
            await inter.response.send_message("Cerrando canal...")
            await asyncio.sleep(3)
            await inter.channel.delete()
            
        close_button.callback = close_callback
        close_view.add_item(close_button)
        
        await ticket_channel.send(embed=embed, view=close_view)
        await interaction.response.send_message(f"✅ Ticket creado en {ticket_channel.mention}", ephemeral=True)

@tree.command(name="setup_tickets", description="Crea un panel de tickets personalizado en un canal específico")
@app_commands.describe(
    titulo="El título que tendrá el panel del ticket",
    descripcion="La descripción o instrucciones dentro del panel",
    canal="El canal donde se enviará el panel",
    tipo="Categoría del ticket (Ej: postulación, compras, soporte)"
)
@app_commands.choices(tipo=[
    app_commands.Choice(name="📜 Postulaciones / Reclutamiento", value="postulacion"),
    app_commands.Choice(name="🛒 Compras / Ventas", value="compras"),
    app_commands.Choice(name="🛠️ Soporte Técnico", value="soporte"),
    app_commands.Choice(name="❓ Consultas Generales", value="general")
])
@app_commands.checks.has_permissions(administrator=True)
async def setup_tickets(
    interaction: discord.Interaction, 
    titulo: str, 
    descripcion: str, 
    canal: discord.TextChannel,
    tipo: app_commands.Choice[str]
):
    embed = discord.Embed(
        title=titulo, 
        description=descripcion, 
        color=discord.Color.purple()
    )
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    
    embed.set_footer(text=f"Sistema de Tickets — {interaction.guild.name}")

    await canal.send(embed=embed, view=TicketButton(ticket_type=tipo.value))
    await interaction.response.send_message(f"✅ Panel de tickets publicado exitosamente en {canal.mention}", ephemeral=True)

# --- EJECUCIÓN ---
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    client.run(TOKEN)
else:
    print("Error: Falta la variable de entorno DISCORD_TOKEN.")
