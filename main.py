import os
import discord
from discord import app_commands
import asyncio
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
from threading import Thread

# --- Truco para Render: Servidor Web en segundo plano ---
def run_health_check():
    # Render asigna un puerto automáticamente en la variable PORT, si no usa el 8080
    port = int(os.environ.get("PORT", 8080))
    handler = SimpleHTTPRequestHandler
    # Permitimos reutilizar el puerto para evitar errores de "Address already in use"
    TCPServer.allow_reuse_address = True
    with TCPServer(("0.0.0.0", port), handler) as httpd:
        print(f"Health check running on port {port}")
        httpd.serve_forever()

# Iniciamos el servidor web en un hilo separado antes de arrancar el bot
Thread(target=run_health_check, daemon=True).start()

# --- Configuración del Bot de Discord ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# --- IDs de Configuración ---
ROLE_VERIFY_ID = 1528762053798662335
WELCOME_CH_ID = 1528749785895538849
LEAVE_CH_ID = 1528750006260072621
INVITE_CH_ID = 1528750567738839150
SHOP_TICKET_CH_ID = 1528754922730815650
SUPPORT_TICKET_CH_ID = 1528755577658937476

@client.event
async def on_ready():
    print(f"Bot conectado como {client.user.name}")
    await client.change_presence(activity=discord.Game(name="vshop.com"))
    try:
        await tree.sync()
        print("Comandos de barra sincronizados correctamente.")
    except Exception as e:
        print(f"Error al sincronizar comandos: {e}")

# --- COMANDO /VERIFY ---
@tree.command(name="verify", description="Crea el panel de verificación profesional de VSHOP")
@app_commands.checks.has_permissions(administrator=True)
async def verify(interaction: discord.Interaction):
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
        embed.set_footer(text="Seguridad de VSHOP", icon_url=interaction.guild.icon.url)
        embed.set_thumbnail(url=interaction.guild.icon.url)
    
    await interaction.response.send_message("Panel creado.", ephemeral=True)
    message = await interaction.channel.send(embed=embed)
    
    emoji = discord.utils.get(interaction.guild.emojis, name="vshop")
    if emoji:
        await message.add_reaction(emoji)

# --- ROL POR REACCIÓN ---
@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == client.user.id:
        return
        
    if payload.emoji.name == "vshop":
        guild = client.get_guild(payload.guild_id)
        if not guild: return
            
        role = guild.get_role(ROLE_VERIFY_ID)
        member = guild.get_member(payload.user_id)
        
        if role and member:
            try:
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

# --- SISTEMA DE TICKETS ---
class TicketButton(discord.ui.View):
    def __init__(self, ticket_type: str):
        super().__init__(timeout=None)
        self.ticket_type = ticket_type

    @discord.ui.button(label="📩 Abrir Ticket", style=discord.ButtonStyle.primary, custom_id="open_ticket_btn")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        category_name = "🛒 TICKETS VENTA" if self.ticket_type == "compras" else "🛠️ TICKETS SOPORTE"
        
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)
            
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            client.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        ticket_channel = await guild.create_text_channel(name=f"{self.ticket_type}-{member.name}", category=category, overwrites=overwrites)
        
        embed = discord.Embed(
            title=f"🎟️ Ticket de {self.ticket_type.capitalize()}",
            description=f"Hola {member.mention}, detalla tu consulta aquí. Un asesor te atenderá pronto.",
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

@tree.command(name="setup_tickets", description="Inicializa los paneles de tickets")
@app_commands.checks.has_permissions(administrator=True)
async def setup_tickets(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    shop_channel = client.get_channel(SHOP_TICKET_CH_ID)
    if shop_channel:
        embed = discord.Embed(title="🛒 TIENDA VSHOP — COMPRAS", description="Abre un ticket pulsando abajo.", color=discord.Color.purple())
        await shop_channel.send(embed=embed, view=TicketButton(ticket_type="compras"))
        
    support_channel = client.get_channel(SUPPORT_TICKET_CH_ID)
    if support_channel:
        embed = discord.Embed(title="🛠️ CENTRO DE SOPORTE — VSHOP", description="Abre un ticket pulsando abajo.", color=discord.Color.orange())
        await support_channel.send(embed=embed, view=TicketButton(ticket_type="soporte"))
        
    await interaction.followup.send("Paneles listos.", ephemeral=True)

# --- EJECUCIÓN ---
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    client.run(TOKEN)
else:
    print("Error: Falta la variable de entorno DISCORD_TOKEN.")