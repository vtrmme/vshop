import os
import discord
from discord import app_commands
from discord.ext import commands

# Configuración de intents necesarios
intents = discord.Intents.default()
intents.members = True  # Crucial para bienvenida, despedida e invitaciones
intents.message_content = True

class VShopBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        # Sincroniza los comandos de barra (/verify, /ad) con Discord
        await self.tree.sync()
        print("Comandos globales sincronizados.")

bot = VShopBot()

# --- CONFIGURACIÓN DE IDs ---
ROLE_VERIFY_ID = 1528762053798662335
WELCOME_CH_ID = 1528749785895538849
LEAVE_CH_ID = 1528750006260072621
INVITE_CH_ID = 1528750567738839150
SHOP_TICKET_CH_ID = 1528754922730815650
SUPPORT_TICKET_CH_ID = 1528755577658937476

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user.name}")
    await bot.change_presence(activity=discord.Game(name="vshop.com"))

# --- COMANDO /VERIFY ---
@bot.tree.command(name="verify", description="Crea el panel de verificación profesional de VSHOP")
@app_commands.checks.has_permissions(administrator=True)
async def verify(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🔒 VERIFICACIÓN REQUERIDA — VSHOP",
        description=(
            "Bienvenido a **VSHOP**. Para acceder al resto de los canales, "
            "tiendas y soporte, debes verificar tu cuenta.\n\n"
            "**Instrucciones:**\n"
            "Reacciona a este mensaje con el emoji <:vshop:1528762053798662335> "
            "(o el emoji personalizado del servidor) para obtener tu rol de acceso."
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text="Seguridad de VSHOP", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
    
    await interaction.response.send_message("Panel creado.", ephemeral=True)
    message = await interaction.channel.send(embed=embed)
    
    # Intentar buscar el emoji personalizado por nombre
    emoji = discord.utils.get(interaction.guild.emojis, name="vshop")
    if emoji:
        await message.add_reaction(emoji)
    else:
        # Si no se encuentra, puedes dejar que reaccionen manualmente o usar uno temporal
        print("Aviso: No se encontró el emoji personalizado ':vshop:'. Asegúrate de que esté subido al servidor.")

# --- ASIGNACIÓN DE ROL POR REACCIÓN ---
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return
        
    # Validamos si el emoji se llama vshop
    if payload.emoji.name == "vshop":
        guild = bot.get_guild(payload.guild_id)
        if not guild:
            return
            
        role = guild.get_role(ROLE_VERIFY_ID)
        member = guild.get_member(payload.user_id)
        
        if role and member:
            try:
                await member.add_roles(role)
                # Enviar un mensaje privado amigable de confirmación
                await member.send(f"✅ ¡Te has verificado correctamente en **{guild.name}**!", delete_after=10)
            except discord.Forbidden:
                print("Error: El bot no tiene permisos suficientes para otorgar este rol. Asegúrate de que el rol del bot esté por encima del rol a otorgar.")

# --- EVENTOS DE BIENVENIDA Y DESPEDIDA ---
@bot.event
async def on_member_join(member: discord.GuildMember):
    # Bienvenida
    welcome_channel = bot.get_channel(WELCOME_CH_ID)
    if welcome_channel:
        embed_welcome = discord.Embed(
            title="👋 ¡Un nuevo miembro ha llegado!",
            description=f"¡Bienvenido/a {member.mention} a **{member.guild.name}**!\nDisfruta de tu estancia y no olvides verificar de en el canal correspondiente.",
            color=discord.Color.green()
        )
        embed_welcome.add_field(name="Miembro número", value=f"#{len(member.guild.members)}", inline=True)
        embed_welcome.set_thumbnail(url=member.display_avatar.url)
        await welcome_channel.send(embed=embed_welcome)

    # Registro de invitación
    invite_channel = bot.get_channel(INVITE_CH_ID)
    if invite_channel:
        # Nota: Para un tracking exacto de quién invitó se requiere un sistema dinámico de caché de invites,
        # aquí enviamos la alerta de que se unió para mantener la estructura limpia.
        embed_invite = discord.Embed(
            title="📥 Registro de Entrada",
            description=f"El usuario {member.name} (`{member.id}`) entró al servidor.",
            color=discord.Color.light_gray()
        )
        await invite_channel.send(embed=embed_invite)

@bot.event
async def on_member_remove(member: discord.GuildMember):
    leave_channel = bot.get_channel(LEAVE_CH_ID)
    if leave_channel:
        embed_leave = discord.Embed(
            title="💔 ¡Alguien nos ha dejado!",
            description=f"Lamentamos ver partir a **{member.name}**.",
            color=discord.Color.red()
        )
        embed_leave.set_thumbnail(url=member.display_avatar.url)
        await leave_channel.send(embed=embed_leave)

# --- COMANDO /AD (ANUNCIOS) ---
@bot.tree.command(name="ad", description="Publica un anuncio profesional en el canal actual")
@app_commands.describe(titulo="El título del anuncio", descripcion="El contenido del anuncio")
@app_commands.checks.has_permissions(administrator=True)
async def ad(interaction: discord.Interaction, titulo: str, descripcion: str):
    embed = discord.Embed(
        title=f"📢 {titulo.upper()}",
        description=descripcion,
        color=discord.Color.gold()
    )
    embed.set_author(name="VSHOP Anuncios", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.set_footer(text=f"Publicado por {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message("Anuncio enviado con éxito.", ephemeral=True)
    await interaction.channel.send(content="@everyone", embed=embed)

# --- SISTEMA DE TICKETS (COMPRAS Y SOPORTE) ---
class TicketButton(discord.ui.View):
    def __init__(self, ticket_type: str):
        super().__init__(timeout=None)
        self.ticket_type = ticket_type # "compras" o "soporte"

    @discord.ui.button(label="📩 Abrir Ticket", style=discord.ButtonStyle.primary, custom_id="open_ticket_btn")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        
        # Crear canales privados según el tipo
        category_name = "🛒 TICKETS VENTA" if self.ticket_type == "compras" else "🛠️ TICKETS SOPORTE"
        
        # Buscar o crear categoría para orden
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)
            
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        channel_name = f"{self.ticket_type}-{member.name}"
        ticket_channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        
        embed_ticket = discord.Embed(
            title=f"🎟️ Ticket de {self.ticket_type.capitalize()}",
            description=f"Hola {member.mention}, gracias por contactar con el equipo de **VSHOP**.\n"
                        f"Por favor, detalla tu consulta o el producto que deseas adquirir aquí. Un asesor te atenderá pronto.",
            color=discord.Color.green()
        )
        
        # Vista interna para cerrar el ticket
        close_view = discord.ui.View(timeout=None)
        close_button = discord.ui.Button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
        
        async def close_callback(inter: discord.Interaction):
            await inter.response.send_message("El ticket se cerrará en 5 segundos...")
            await asyncio.sleep(5)
            await inter.channel.delete()
            
        close_button.callback = close_callback
        close_view.add_item(close_button)
        
        await ticket_channel.send(embed=embed_ticket, view=close_view)
        await interaction.response.send_message(f"✅ Tu ticket ha sido creado en {ticket_channel.mention}", ephemeral=True)

# Comando para inicializar los paneles de Tickets (Ejecutar una vez por staff)
@bot.tree.command(name="setup_tickets", description="Inicializa los paneles de tickets en sus canales respectivos")
@app_commands.checks.has_permissions(administrator=True)
async def setup_tickets(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    # Canal de Compras
    shop_channel = bot.get_channel(SHOP_TICKET_CH_ID)
    if shop_channel:
        embed_shop = discord.Embed(
            title="🛒 TIENDA VSHOP — COMPRAS",
            description="Si deseas adquirir alguno de nuestros productos, servicios o rangos, abre un ticket de compra pulsando el botón de abajo.",
            color=discord.Color.purple()
        )
        await shop_channel.send(embed=embed_shop, view=TicketButton(ticket_type="compras"))
        
    # Canal de Soporte
    support_channel = bot.get_channel(SUPPORT_TICKET_CH_ID)
    if support_channel:
        embed_support = discord.Embed(
            title="🛠️ CENTRO DE SOPORTE — VSHOP",
            description="¿Tienes problemas, dudas o reportes? Nuestro equipo está listo para ayudarte. Dale clic al botón inferior.",
            color=discord.Color.orange()
        )
        await support_channel.send(embed=embed_support, view=TicketButton(ticket_type="soporte"))
        
    await interaction.followup.send("Paneles de tickets creados con éxito en sus canales correspondientes.", ephemeral=True)

# --- EJECUCIÓN (Llamando la variable de Render) ---
import asyncio
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: No se encontró la variable de entorno 'DISCORD_TOKEN'.")